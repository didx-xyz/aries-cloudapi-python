from typing import Any, Dict, Optional

from dependency_injector.wiring import Provide, inject
from fastapi import Depends, Request, status

from shared import APIRouter
from shared.log_config import get_logger
from shared.models.webhook_topics import (
    AcaPyWebhookEvent,
    CloudApiWebhookEvent,
    topic_mapping,
)
from webhooks.models import acapy_to_cloudapi_event
from webhooks.services.dependency_injection.container import Container
from webhooks.services.redis_service import RedisService

logger = get_logger(__name__)

router = APIRouter()


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
    try:
        wallet_id = request.headers["x-wallet-id"]
    except KeyError:
        ## TODO: implement different wallet_id for events from governance agent
        # if origin == "governance":
        #     wallet_id = origin
        # else:
        wallet_id = "admin"

    bound_logger = logger.bind(
        body={
            "wallet_id": wallet_id,
            "acapy_topic": acapy_topic,
            "origin": origin,
            "body": body,
        }
    )
    bound_logger.debug("Handling received webhook event")

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

    webhook_event_json = cloudapi_webhook_event.model_dump_json()

    # Add data to redis, which publishes to a redis pubsub channel that SseManager listens to
    await redis_service.add_webhook_event(webhook_event_json, wallet_id)

    bound_logger.trace("Successfully processed received webhook.")
