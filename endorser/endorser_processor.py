import asyncio
from typing import Any, Dict

from aries_cloudcontroller import AcaPyClient
from fastapi import HTTPException
from fastapi_websocket_pubsub import PubSubClient
from pydantic import BaseModel

from endorser.utils.transaction_record import (
    get_did_and_schema_id_from_cred_def_attachment,
    get_endorsement_request_attachment,
    is_credential_definition_transaction,
)
from endorser.utils.trust_registry import is_valid_issuer
from shared import GOVERNANCE_AGENT_API_KEY, GOVERNANCE_AGENT_URL, WEBHOOKS_PUBSUB_URL
from shared.log_config import get_logger
from shared.models.webhook_topics import Endorsement
from shared.util.rich_parsing import parse_with_error_handling

logger = get_logger(__name__)


class Event(BaseModel):
    payload: Dict[str, Any]
    origin: str
    wallet_id: str


async def listen_endorsement_events():
    topic = "endorsements-governance"

    client = PubSubClient([topic], callback=process_endorsement_event)
    logger.debug("Opening connection to webhook server")
    client.start_client(WEBHOOKS_PUBSUB_URL)
    logger.debug("Opened connection to webhook server. Waiting for readiness...")
    await client.wait_until_ready()
    logger.debug("Connection to webhook server ready")
    logger.info(
        "Listening for 'endorsements' events from webhook server at {}.",
        WEBHOOKS_PUBSUB_URL,
    )


# topic is unused, but passed by the fastapi library.
async def process_endorsement_event(data: str, topic: str):
    event: Event = parse_with_error_handling(Event, data)
    logger.debug(
        "Processing endorsement event for agent `{}` and wallet `{}`",
        event.origin,
        event.wallet_id,
    )
    # We're only interested in events from the governance agent
    if not is_governance_agent(event):
        logger.debug("Endorsement request is not for governance agent.")
        return

    endorsement = Endorsement(**event.payload)

    async with AcaPyClient(
        base_url=GOVERNANCE_AGENT_URL, api_key=GOVERNANCE_AGENT_API_KEY
    ) as client:
        # Not interested in this endorsement request
        if not await should_accept_endorsement(client, endorsement):
            logger.debug(
                "Endorsement request with transaction id `{}` is not applicable for endorsement.",
                endorsement.transaction_id,
            )
            return

        logger.info(
            "Endorsement request with transaction id `{}` is applicable for endorsement, accepting request.",
            endorsement.transaction_id,
        )
        await accept_endorsement(client, endorsement)


def is_governance_agent(event: Event):
    return event.origin == "governance"


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
    bound_logger = logger.bind(body=endorsement)
    bound_logger.debug("Validating if endorsement transaction should be endorsed")

    transaction_id = endorsement.transaction_id
    bound_logger.debug("Fetching transaction with id: `{}`", transaction_id)
    transaction = await client.endorse_transaction.get_transaction(
        tran_id=transaction_id
    )

    if transaction.state != "request_received":
        bound_logger.debug(
            "Endorsement event for transaction with id `{}` "
            "not in state 'request_received' (is `{}`).",
            transaction_id,
            transaction.state,
        )
        return False

    attachment = get_endorsement_request_attachment(transaction)

    if not attachment:
        bound_logger.debug("Could not extract attachment from transaction.")
        return False

    if not is_credential_definition_transaction(attachment):
        bound_logger.debug("Endorsement request is not for credential definition.")
        return False

    if "identifier" not in attachment:
        bound_logger.debug(
            "Expected key `identifier` does not exist in extracted attachment. Got attachment: `{}`.",
            attachment,
        )
        return False

    # `operation` key is asserted to exist in `is_credential_definition_transaction`
    if "ref" not in attachment["operation"]:
        bound_logger.debug(
            "Expected key `ref` does not exist in attachment `operation`. Got operation: `{}`.",
            attachment["operation"],
        )
        return False

    did, schema_id = await get_did_and_schema_id_from_cred_def_attachment(
        client, attachment
    )

    max_retries = 5
    retry_delay = 1  # in seconds

    for attempt in range(max_retries):
        try:
            valid_issuer = await is_valid_issuer(did, schema_id)

            if not valid_issuer:
                bound_logger.info(
                    "Endorsement request with transaction id `{}` is not for did "
                    "and schema registered in the trust registry.",
                    transaction_id,
                )
                return False

            return True

        except HTTPException as e:
            bound_logger.error(
                "Attempt {}: Exception caught when asserting valid issuer: {}",
                attempt + 1,
                e,
            )

            if attempt < max_retries - 1:
                bound_logger.info("Retrying...")
                await asyncio.sleep(retry_delay)
            else:
                bound_logger.error("Max retries reached. Giving up.")
                return False


async def accept_endorsement(client: AcaPyClient, endorsement: Endorsement):
    logger.debug("Endorsing transaction with id: `{}`", endorsement.transaction_id)
    await client.endorse_transaction.endorse_transaction(
        tran_id=endorsement.transaction_id
    )
