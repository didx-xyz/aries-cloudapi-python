from typing import Any, Dict

from aries_cloudcontroller import AcaPyClient
from fastapi_websocket_pubsub import PubSubClient
from pydantic import BaseModel

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
