import logging
from typing import Any, List

from dependency_injector.wiring import Provide, inject
from fastapi import Depends

from shared import APIRouter, TopicItem
from webhooks.dependencies.container import Container
from webhooks.dependencies.service import Service

LOGGER = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks")


# Routes are duplicated with trailing slash to avoid unnecessary redirects
@router.get(
    "/{wallet_id}",
    summary="Subscribe or get all webhook events for a wallet ID",
)
@inject
async def wallet_root(
    wallet_id: str, service: Service = Depends(Provide[Container.service])
):
    data = await service.get_all_by_wallet(wallet_id)
    return data


@router.get(
    "/{wallet_id}/{topic}",
    summary="Subscribe or get all webhook events for a topic and wallet ID",
)
@inject
async def wallet_hooks(
    topic: str,
    wallet_id: str,
    service: Service = Depends(Provide[Container.service]),
) -> List[TopicItem[Any]]:
    data = await service.get_all_for_topic_by_wallet_id(
        topic=topic, wallet_id=wallet_id
    )
    return data
