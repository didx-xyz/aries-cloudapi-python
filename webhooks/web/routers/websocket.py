from fastapi import APIRouter
from fastapi_websocket_pubsub import PubSubEndpoint

from shared.log_config import get_logger

logger = get_logger(__name__)

router = APIRouter()

endpoint = PubSubEndpoint()
endpoint.register_route(router, "/pubsub")


async def publish_event_on_websocket(
    event_json: str, group_id: str, wallet_id: str, topic: str
) -> None:
    """
    Publish the webhook to websocket subscribers on the following topics:
        - for the group_id
        - for the group_id - wallet_id pair
        - for the group_id - topic pair
        - for the group_id - wallet_id - topic combo

    Args:
        event_json (str): Webhook event serialized as json
        group_id (str): The group_id that wallet belongs to
        wallet_id (str): The wallet_id for this event
        topic (str): The cloudapi topic for the event
    """
    group_wallet = f"{group_id}:{wallet_id}"
    group_topic = f"{group_id}:{topic}"
    group_wallet_topic = f"{group_id}:{wallet_id}:{topic}"

    publish_topics = [group_wallet, group_topic, group_wallet_topic]
    if group_id:  # don't publish on empty string if group_id is blank
        publish_topics += [group_id]

    logger.trace("Publishing event on websocket: {}", event_json)
    await endpoint.publish(topics=publish_topics, data=event_json)
