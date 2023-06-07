import json
import logging
from typing import Any, Dict, Optional, TypedDict

import httpx
from aries_cloudcontroller import AcaPyClient, TransactionRecord
from fastapi_websocket_pubsub import PubSubClient

from shared import (
    GOVERNANCE_AGENT_API_KEY,
    GOVERNANCE_AGENT_URL,
    TRUST_REGISTRY_URL,
    WEBHOOKS_PUBSUB_URL,
    Endorsement,
)

logger = logging.getLogger(__name__)


class Event(TypedDict):
    payload: Dict[str, Any]
    origin: str
    wallet_id: str


async def listen_endorsement_events():
    topic = "endorsements-admin"

    client = PubSubClient([topic], callback=process_endorsement_event)
    logger.debug("Opening connection to webhook server")
    client.start_client(WEBHOOKS_PUBSUB_URL)
    logger.debug("Opened connection to webhook server. waiting for readiness...")
    await client.wait_until_done()
    logger.debug("Connection to webhook server ready")
    logger.info(
        "Listening for 'endorsements' events from webhook server at %s",
        WEBHOOKS_PUBSUB_URL,
    )


# topic is unused, but passed by the fastapi library.
async def process_endorsement_event(data: str, topic: str):
    event: Event = json.loads(data)
    logger.debug(
        "Processing endorsement event for agent %s (%s)",
        event["origin"],
        event["wallet_id"],
    )
    # We're only interested in events from the governance agent
    if not is_governance_agent(event):
        logger.debug("Endorsement request is not for governance agent.")
        return

    endorsement = Endorsement(**event["payload"])

    async with AcaPyClient(
        base_url=GOVERNANCE_AGENT_URL, api_key=GOVERNANCE_AGENT_API_KEY
    ) as client:
        # Not interested in this endorsement request
        if not await should_accept_endorsement(client, endorsement):
            logger.debug(
                "Endorsement request with transaction id %s is not applicable for endorsement.",
                endorsement.transaction_id,
            )
            return

        logger.debug(
            "Endorsement request with transaction id %s is applicable for endorsement, accepting request.",
            endorsement.transaction_id,
        )
        await accept_endorsement(client, endorsement)


def is_governance_agent(event: Event):
    return event["origin"] == "governance"


async def should_accept_endorsement(
    client: AcaPyClient, endorsement: Endorsement
) -> bool:
    """Check whether a transaction endorsement request should be endorsed.

    Whether the request should be accepted is based on the follow criteria:
    1. The transaction is for a credential definition
    2. The did is registered as an issuer in the trust registry.
    3. The schema_id is registered in the trust registry.

    Args:
        endorsement (Endorsement): The endorsement event model

    Returns:
        bool: Whether the endorsement request should be accepted
    """

    transaction = await client.endorse_transaction.get_transaction(
        tran_id=endorsement.transaction_id
    )

    if transaction.state != "request_received":
        logger.debug(
            "Endorsement event for transaction with id '%s' not in state 'request_received' (is '%s').",
            transaction.transaction_id,
            transaction.state,
        )
        return False

    attachment = get_endorsement_request_attachment(transaction)

    if not attachment:
        logger.debug("Could not extract attachment from transaction.")
        return False

    if not is_credential_definition_transaction(attachment):
        logger.debug(
            "Endorsement request with transaction id %s is not for credential definition.",
            endorsement.transaction_id,
        )
        return False

    did, schema_id = await get_did_and_schema_id_from_cred_def_attachment(
        client, attachment
    )

    if not await is_valid_issuer(did, schema_id):
        logger.debug(
            "Endorsement request with transaction id %s is not for did and schema registered in the trust registry.",
            endorsement.transaction_id,
        )
        return False

    return True


async def get_did_and_schema_id_from_cred_def_attachment(
    client: AcaPyClient, attachment: Dict[str, Any]
):
    did = "did:sov:" + attachment["identifier"]
    schema_seq_id = attachment["operation"]["ref"]

    schema = await client.schema.get_schema(schema_id=schema_seq_id)

    if not schema.schema_ or not schema.schema_.id:
        raise Exception("Could not extract schema id from schema response")

    schema_id = schema.schema_.id

    return (did, schema_id)


def get_endorsement_request_attachment(
    transaction: TransactionRecord,
) -> Optional[Dict[str, Any]]:
    try:
        if not transaction.messages_attach:
            return None

        attachment = transaction.messages_attach[0]
        json_payload = attachment["data"]["json"]

        # Both dict and str encoding have ocurred for the attachment data
        # Parse to dict if payload is of type str
        if isinstance(json_payload, str):
            json_payload = json.loads(json_payload)

        return json_payload
    except Exception as e:
        logger.debug(
            "Exception caught while running `get_endorsement_request_attachment`. %r", e
        )
        return None


def is_credential_definition_transaction(attachment: Dict[str, Any]) -> bool:
    try:
        operation = attachment["operation"]

        logger.debug(
            "Endorsement request operation type: %s. Need 102", operation.get("type")
        )

        # credential definition type is 102
        # see https://github.com/hyperledger/indy-node/blob/master/docs/source/requests.md#common-request-structure
        return operation.get("type") == "102"
    except Exception as e:
        logger.debug(
            "Exception caught while running `is_credential_definition_transaction`. %r",
            e,
        )
        return False


async def is_valid_issuer(did: str, schema_id: str):
    """Assert that an actor with the specified did is registered as issuer.

    This method asserts that there is an actor registered in the trust registry
    with the specified did. It verifies whether this actor has the `issuer` role
    and will also make sure the specified schema_id is registered as a valid schema.
    Raises an exception if one of the assertions fail.

    NOTE: the dids in the registry are registered as fully qualified dids. This means
    when passing a did to this method it must also be fully qualified (e.g. `did:sov:xxxx`)

    Args:
        did (str): the did of the issuer in fully qualified format.
        schema_id (str): the schema_id of the credential being issued

    Raises:
        Exception: When the did is not registered, the actor doesn't have the issuer role
            or the schema is not registered in the registry.
    """
    try:
        with httpx.Client() as client:
            actor_res = client.get(f"{TRUST_REGISTRY_URL}/registry/actors/did/{did}")
    except httpx.HTTPError as e:
        raise e from e

    if actor_res.is_error:
        logger.error(
            "Error retrieving actor for did %s from trust registry. %s",
            did,
            actor_res.text,
        )
        return False
    actor = actor_res.json()

    # We need role issuer
    if "issuer" not in actor["roles"]:
        actor_id = actor["id"]
        logger.error("Actor %s does not have required role 'issuer'", actor_id)
        return False

    try:
        with httpx.Client() as client:
            schema_res = client.get(f"{TRUST_REGISTRY_URL}/registry/schemas")
    except httpx.HTTPError as e:
        raise e from e

    if schema_res.is_error:
        logger.error(
            "Error retrieving schemas from trust registry. %s", schema_res.text
        )
        return False

    schemas = schema_res.json()["schemas"]
    if schema_id not in schemas:
        logger.error("schema %s not in the trust registry.", schema_id)
        return False

    return True


async def accept_endorsement(client: AcaPyClient, endorsement: Endorsement):
    await client.endorse_transaction.endorse_transaction(
        tran_id=endorsement.transaction_id
    )
