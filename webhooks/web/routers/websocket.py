from fastapi import APIRouter
from fastapi_websocket_pubsub import PubSubEndpoint

from shared.models.webhook_topics import WEBHOOK_TOPIC_ALL

router = APIRouter()

endpoint = PubSubEndpoint()
endpoint.register_route(router, "/pubsub")


async def publish_event_on_websocket(
    event_json: str, wallet_id: str, topic: str
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
    """

    publish_topics = [topic, wallet_id, f"{topic}-{wallet_id}", WEBHOOK_TOPIC_ALL]

    await endpoint.publish(topics=publish_topics, data=event_json)
