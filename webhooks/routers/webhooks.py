from typing import Any, List

from dependency_injector.wiring import Provide, inject
from fastapi import Depends

from shared import APIRouter
from shared.log_config import get_logger
from shared.models.topics import CloudApiWebhookEvent
from webhooks.dependencies.container import Container
from webhooks.dependencies.redis_service import RedisService

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks")


# Routes are duplicated with trailing slash to avoid unnecessary redirects
@router.get(
    "/{wallet_id}",
    summary="Get all webhook events for a wallet ID",
)
@inject
async def wallet_root(
    wallet_id: str,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
):
    bound_logger = logger.bind(body={"wallet_id": wallet_id})
    bound_logger.info("GET request received: Fetch all webhook events for wallet")

    data = await redis_service.get_all_by_wallet(wallet_id)

    if data:
        bound_logger.info("Successfully fetched webhooks events for wallet.")
    else:
        bound_logger.info("No webhooks events returned for wallet.")
    return data


@router.get(
    "/{wallet_id}/{topic}",
    summary="Get all webhook events for a wallet ID and topic pair",
)
@inject
async def wallet_hooks(
    topic: str,
    wallet_id: str,
    redis_service: RedisService = Depends(Provide[Container.redis_service]),
) -> List[CloudApiWebhookEvent[Any]]:
    bound_logger = logger.bind(body={"wallet_id": wallet_id, "topic": topic})
    bound_logger.info(
        "GET request received: Fetch all webhook events for wallet and topic"
    )

    data = await redis_service.get_all_for_topic_by_wallet_id(
        topic=topic, wallet_id=wallet_id
    )

    if data:
        bound_logger.info("Successfully fetched webhooks events for wallet and topic.")
    else:
        bound_logger.info("No webhooks events returned for wallet and topic pair.")
    return data
