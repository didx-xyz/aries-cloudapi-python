from typing import List

from dependency_injector.wiring import Provide, inject
from fastapi import Depends

from shared import APIRouter
from shared.log_config import get_logger
from shared.models.webhook_topics import CloudApiWebhookEvent
from webhooks.dependencies.container import Container
from webhooks.dependencies.redis_service import RedisService

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks")


# Routes are duplicated with trailing slash to avoid unnecessary redirects
@router.get(
    "/{wallet_id}",
    summary="Get all webhook events for a wallet ID",
    response_model=List[CloudApiWebhookEvent],
)
@inject
async def get_webhooks_by_wallet(
    wallet_id: str,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
) -> List[str]:
    bound_logger = logger.bind(body={"wallet_id": wallet_id})
    bound_logger.info("GET request received: Fetch all webhook events for wallet")

    data = await redis_service.get_json_webhook_events_by_wallet(wallet_id)

    if data:
        bound_logger.info("Successfully fetched webhooks events for wallet.")
    else:
        bound_logger.info("No webhooks events returned for wallet.")
    return data


@router.get(
    "/{wallet_id}/{topic}",
    summary="Get all webhook events for a wallet ID and topic pair",
    response_model=List[CloudApiWebhookEvent],
)
@inject
async def get_webhooks_by_wallet_and_topic(
    topic: str,
    wallet_id: str,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
) -> List[str]:
    bound_logger = logger.bind(body={"wallet_id": wallet_id, "topic": topic})
    bound_logger.info(
        "GET request received: Fetch all webhook events for wallet and topic"
    )

    data = await redis_service.get_json_webhook_events_by_wallet_and_topic(
        wallet_id=wallet_id, topic=topic
    )

    if data:
        bound_logger.info("Successfully fetched webhooks events for wallet and topic.")
    else:
        bound_logger.info("No webhooks events returned for wallet and topic pair.")
    return data
