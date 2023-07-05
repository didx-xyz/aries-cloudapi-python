from typing import Any, List

from dependency_injector.wiring import Provide, inject
from fastapi import Depends

from shared import APIRouter, TopicItem
from webhooks.config.log_config import get_logger
from webhooks.dependencies.container import Container
from webhooks.dependencies.service import Service

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks")


# Routes are duplicated with trailing slash to avoid unnecessary redirects
@router.get(
    "/{wallet_id}",
    summary="Get all webhook events for a wallet ID",
)
@inject
async def wallet_root(
    wallet_id: str, service: Service = Depends(Provide[Container.service])
):
    bound_logger = logger.bind(body={"wallet_id": wallet_id})
    bound_logger.info("GET request received: Fetch all webhook events for wallet")

    data = await service.get_all_by_wallet(wallet_id)

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
    service: Service = Depends(Provide[Container.service]),
) -> List[TopicItem[Any]]:
    bound_logger = logger.bind(body={"wallet_id": wallet_id, "topic": topic})
    bound_logger.info(
        "GET request received: Fetch all webhook events for wallet and topic"
    )

    data = await service.get_all_for_topic_by_wallet_id(
        topic=topic, wallet_id=wallet_id
    )

    if data:
        bound_logger.info("Successfully fetched webhooks events for wallet and topic.")
    else:
        bound_logger.info("No webhooks events returned for wallet and topic pair.")
    return data
