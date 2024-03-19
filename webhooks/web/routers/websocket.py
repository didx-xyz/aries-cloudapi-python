from typing import Optional

from fastapi import APIRouter
from fastapi_websocket_pubsub import PubSubEndpoint

from shared.log_config import get_logger
from shared.models.webhook_events import WEBHOOK_TOPIC_ALL

logger = get_logger(__name__)

router = APIRouter()

endpoint = PubSubEndpoint()
endpoint.register_route(router, "/pubsub")


async def publish_event_on_websocket(
    event_json: str, wallet_id: str, topic: str, group_id: Optional[str] = None
) -> None:
    """
    Publish the webhook to websocket subscribers on the following topics:
        - current wallet id
        - topic of the event
        - topic and wallet id combined as topic-wallet_id
        - 'all' topic, which allows to subscribe to all published events

    Args:
        event_json (str): Webhook event serialized as json
        wallet_id (str): The wallet_id for this event
        topic (str): The cloudapi topic for the event
        group_id (Optional[str]): The group_id that the wallet belongs to
    """

    publish_topics = [topic, wallet_id, f"{topic}-{wallet_id}", WEBHOOK_TOPIC_ALL]
    logger.trace("Publishing event on websocket: {}", event_json)
    await endpoint.publish(topics=publish_topics, data=event_json)
