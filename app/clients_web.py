import asyncio
import json
import os
import sys
from typing import Any, Dict

import aioredis
from aioredis import Redis
from aries_cloudcontroller import AcaPyClient, TransactionRecord
from fastapi_websocket_pubsub import PubSubClient
from httpx import AsyncClient, HTTPStatusError
from pydantic import BaseModel

from shared.constants import GOVERNANCE_AGENT_API_KEY, GOVERNANCE_AGENT_URL
from shared.util.rich_parsing import parse_with_error_handling

LAGO_URL = "http://localhost:3000/api/v1/events"
LAGO_API_KEY = "cb131628-c605-49bd-8aa3-93fe0289e1a3"
PORT = os.getenv("PORT", "3010")
URL = os.getenv("WEBHOOKS_URL", "localhost")


class Event(BaseModel):
    payload: Dict[str, Any]
    origin: str
    wallet_id: str
    topic: str


class LagoEvent(BaseModel):
    external_customer_id: str
    transaction_id: str
    code: str
    # external_subscription_id: str


class GetTransactionError(Exception):
    """Raise when unable to get endorsement transaction"""


sys.path.append(os.path.abspath(os.path.join(os.path.basename(__file__), "..")))


async def on_events(data, topic):
    redis = await aioredis.from_url("redis://localhost:6381", decode_responses=True)
    event: Event = parse_with_error_handling(Event, data)
    print(f"\n {event.topic} \n")

    if (
        event.origin == "governance"
        and event.topic == "endorsements"
        and event.payload["state"] == "transaction-acked"
    ):
        await get_transaction(event, redis)
    elif (
        event.origin == "multitenant"
        and event.topic == "proofs"
        and event.payload["role"] == "verifier"
        and event.payload["state"] == "done"
    ):
        await convert_proof_event(event, redis)
    elif (
        event.origin == "multitenant"
        and event.topic == "credentials"
        and event.payload["role"] == "issuer"
        and event.payload["state"] == "done"
    ):
        await convert_issue_event(event, redis)
    elif (
        event.origin == "multitenant"
        and event.topic == "revocation"
        and event.payload["state"] == "posted"
    ):
        #this happens when a cred_def is created with revocation enabled
        #print(f"Revocation ==> \n {event} \n")
        await convert_revocation_event(event, redis)


async def main():
    """
    # You can also register it using the commented code below
    async def on_data(data, topic):
        print(f"{topic}:\n", data)

    [client.subscribe(topic, on_data) for topic in topics]
    """
    # Create a client and subscribe to topics
    client = PubSubClient(["ALL_WEBHOOKS"], callback=on_events)

    client.start_client(f"ws://{URL}:{PORT}/pubsub")
    print(f"Started on: ws://{URL}:{PORT}/pubsub \n")
    await client.wait_until_done()


async def get_transaction(event: Event, redis: Redis):
    async with AcaPyClient(
        base_url=GOVERNANCE_AGENT_URL, api_key=GOVERNANCE_AGENT_API_KEY
    ) as acapy_client:
        transaction: TransactionRecord = (
            await acapy_client.endorse_transaction.get_transaction(
                tran_id=event.payload["transaction_id"]
            )
        )

        if not transaction.messages_attach:
            raise GetTransactionError("No Attachment in Transaction")

        attachment: Dict = transaction.messages_attach[0]

        # print(f"Attachment ==> \n {attachment} \n")

        if "data" not in attachment:
            raise GetTransactionError("No Data in attachment")

        if not isinstance(attachment["data"], dict) or "json" not in attachment["data"]:
            raise GetTransactionError("No Json in Attachment[Data]")

        json_payload = attachment["data"]["json"]

        if isinstance(json_payload, str):
            try:
                json_payload = json.loads(json_payload)
            except json.JSONDecodeError:
                raise

            related_did = f"did:sov:{json_payload['identifier']}"

            try:
                async with AsyncClient() as client:
                    while True:
                        actor_response = await client.get(
                            url=f"http://localhost:8100/trust-registry/actors?actor_did={related_did}"
                        )

                        if actor_response.status_code != 404:
                            break
                    actor_response.raise_for_status()
                    actor = (actor_response.json())[0]

            except Exception as e:
                print(f"Get actor error {e}")
                raise e

            group_id = await redis.get(actor["id"])

            if json_payload["operation"]["type"] == "100":
                lago_event = {
                    "transaction_id": event.payload["transaction_id"],
                    "external_customer_id": group_id,
                    "code": "attrib",
                }

                await push_event_to_lago(lago_event)

            elif json_payload["operation"]["type"] == "102":
                lago_event = {
                    "transaction_id": event.payload["transaction_id"],
                    "external_customer_id": group_id,
                    "code": "cred_def",
                }

                await push_event_to_lago(lago_event)


async def convert_proof_event(event: Event, redis: Redis):
    # convert event to lago_event

    group_id = await redis.get(event.wallet_id)

    lago_event = {
        "transaction_id": event.payload["thread_id"],
        "external_customer_id": group_id,
        "code": "proof_done",
    }

    await push_event_to_lago(lago_event)


async def convert_issue_event(event: Event, redis: Redis):
    # convert event to lago_event

    group_id = await redis.get(event.wallet_id)

    lago_event = {
        "transaction_id": event.payload["thread_id"],
        "external_customer_id": group_id,
        "code": "issue_done",
    }

    await push_event_to_lago(lago_event)


async def push_event_to_lago(lago_event: LagoEvent):
    headers = {"Authorization": f"Bearer {LAGO_API_KEY}"}
    # print(f"LAGO_EVENT ===> \n {lago_event} \n")
    try:
        async with AsyncClient() as client:
            lago_response = await client.post(
                url=LAGO_URL, headers=headers, json={"event": lago_event}
            )
            lago_response.raise_for_status()
    except HTTPStatusError as e:
        print(f"ERROR ==> \n {e} \n")
        raise e


asyncio.run(main())
