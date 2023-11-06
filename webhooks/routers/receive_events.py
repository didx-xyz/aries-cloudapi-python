from typing import Any, Dict

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
from webhooks.dependencies.sse_manager import SseManager

logger = get_logger(__name__)

router = APIRouter()

endpoint = PubSubEndpoint()
endpoint.register_route(router, "/pubsub")


# 'origin' helps to distinguish where a hook is from
# eg the admin, tenant or OP agent respectively
@router.post(
    "/{origin}/topic/{acapy_topic}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Receive webhook events from ACA-Py",
)
@inject
async def topic_root(
    acapy_topic: str,
    origin: str,
    body: Dict[str, Any],
    request: Request,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
    sse_manager: SseManager = Depends(Provide[Container.sse_manager]),
):
    bound_logger = logger.bind(
        body={"acapy_topic": acapy_topic, "origin": origin, "body": body}
    )
    bound_logger.debug("Handling received event")

    try:
        wallet_id = request.headers["x-wallet-id"]
    except KeyError:
        bound_logger.info(
            "No `x-wallet-id` in headers for this received event. "
            "Defaulting wallet_id to admin"
        )
        # FIXME: wallet_id is admin for all admin wallets from different origins. We should make a difference on this
        # Maybe the wallet id should be the role (governance, tenant-admin)?
        wallet_id = "admin"

    # Map from the acapy webhook topic to a unified cloud api topic
    topic = topic_mapping.get(acapy_topic)
    if not topic:
        bound_logger.warning(
            "Not publishing webhook event for acapy_topic `{}` as it doesn't exist in the topic_mapping",
            acapy_topic,
        )
        return

    incoming_webhook_event: AcaPyWebhookEvent = AcaPyWebhookEvent(
        payload=body,
        origin=origin,
        topic=topic,
        acapy_topic=acapy_topic,
        wallet_id=wallet_id,
    )

    event_payload: CloudApiWebhookEvent = redis_service.transform_topic_entry(
        incoming_webhook_event
    )
    if not event_payload:
        bound_logger.warning(
            "Not publishing webhook event for topic `{}` as no transformer exists for the topic",
            topic,
        )
        return

    # Enqueue the event for SSE
    await sse_manager.enqueue_sse_event(event_payload)

    # publish the webhook to subscribers for the following topics
    #  - current wallet id
    #  - topic of the event
    #  - topic and wallet id combined as topic-wallet_id
    #    - this allows for fine grained subscriptions (i.e. the endorser service)
    #  - 'all' topic, which allows to subscribe to all published events
    await endpoint.publish(
        topics=[
            topic,
            wallet_id,
            f"{topic}-{wallet_id}",
            WEBHOOK_TOPIC_ALL,
        ],
        data=event_payload.model_dump_json(),
    )

    # Add data to redis
    await redis_service.add_wallet_entry(incoming_webhook_event)

    logger.debug("Successfully processed received webhook.")
