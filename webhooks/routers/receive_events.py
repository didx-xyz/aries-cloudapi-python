from typing import Any, Dict, Optional

from dependency_injector.wiring import Provide, inject
from fastapi import Depends, Request, status
from fastapi_websocket_pubsub import PubSubEndpoint

from shared import APIRouter
from shared.log_config import get_logger
from shared.models.webhook_topics import (
    WEBHOOK_TOPIC_ALL,
    AcaPyWebhookEvent,
    CloudApiWebhookEvent,
    topic_mapping,
)
from webhooks.dependencies.container import Container
from webhooks.dependencies.redis_service import RedisService
from webhooks.models import acapy_to_cloudapi_event

logger = get_logger(__name__)

router = APIRouter()

endpoint = PubSubEndpoint()
endpoint.register_route(router, "/pubsub")


@router.post(
    "/{origin}/topic/{acapy_topic}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Receive webhook events from ACA-Py",
)
@inject
async def topic_root(
    origin: str,  # 'origin' helps to distinguish where a hook is from, i.e. governance or multitenant agent
    acapy_topic: str,
    body: Dict[str, Any],
    request: Request,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
):
    bound_logger = logger.bind(
        body={"acapy_topic": acapy_topic, "origin": origin, "body": body}
    )
    bound_logger.debug("Handling received webhook event")

    try:
        wallet_id = request.headers["x-wallet-id"]
    except KeyError:
        if origin == "governance":
            wallet_id = origin
        else:
            wallet_id = "admin"
    bound_logger.trace("Wallet_id for this event: {}", wallet_id)

    # Map from the acapy webhook topic to a unified cloud api topic
    cloudapi_topic = topic_mapping.get(acapy_topic)
    if not cloudapi_topic:
        bound_logger.warning(
            "Not publishing webhook event for acapy_topic `{}` as it doesn't exist in the topic_mapping",
            acapy_topic,
        )
        return

    acapy_webhook_event = AcaPyWebhookEvent(
        payload=body,
        wallet_id=wallet_id,
        acapy_topic=acapy_topic,
        topic=cloudapi_topic,
        origin=origin,
    )

    cloudapi_webhook_event: Optional[CloudApiWebhookEvent] = acapy_to_cloudapi_event(
        acapy_webhook_event
    )
    if not cloudapi_webhook_event:
        bound_logger.warning(
            "Not publishing webhook event for topic `{}` as no transformer exists for the topic",
            cloudapi_topic,
        )
        return

    # publish the webhook to subscribers for the following topics
    #  - current wallet id
    #  - topic of the event
    #  - topic and wallet id combined as topic-wallet_id
    #    - this allows for fine grained subscriptions (i.e. the endorser service)
    #  - 'all' topic, which allows to subscribe to all published events
    webhook_event_json = cloudapi_webhook_event.model_dump_json()
    await endpoint.publish(
        topics=[
            cloudapi_topic,
            wallet_id,
            f"{cloudapi_topic}-{wallet_id}",
            WEBHOOK_TOPIC_ALL,
        ],
        data=webhook_event_json,
    )

    # Add data to redis, which publishes to a redis pubsub channel that SseManager listens to
    await redis_service.add_webhook_event(wallet_id, webhook_event_json)

    logger.debug("Successfully processed received webhook.")
