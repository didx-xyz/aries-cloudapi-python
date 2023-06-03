import logging
from typing import Any, List

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from shared import TopicItem
from webhooks.dependencies.container import Container
from webhooks.dependencies.service import Service

LOGGER = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks")


# Routes are duplicated with trailing slash to avoid unnecessary redirects
@router.get(
    "/webhooks/{wallet_id}",
    summary="Subscribe or get all webhook events for a wallet ID",
)
@router.get("/webhooks/{wallet_id}/", include_in_schema=False)
@inject
async def wallet_root(
    wallet_id: str, service: Service = Depends(Provide[Container.service])
):
    data = await service.get_all_by_wallet(wallet_id)
    return data


@router.get(
    "/webhooks/{topic}/{wallet_id}",
    summary="Subscribe or get all webhook events for a topic and wallet ID",
)
@router.get("/webhooks/{topic}/{wallet_id}/", include_in_schema=False)
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
