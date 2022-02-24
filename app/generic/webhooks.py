import logging
from typing import List
from aries_cloudcontroller import AcaPyClient

from fastapi import APIRouter, Depends

from app.dependencies import agent_selector
from app.facades.webhooks import (
    get_hooks_per_wallet,
    get_hooks_per_topic_per_wallet,
    topics,
)
from shared_models import TopicItem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("/")
async def get_webhooks_for_wallet(
    aries_controller: AcaPyClient = Depends(agent_selector),
) -> List[TopicItem]:
    """
    Returns all webhooks per wallet

    This implicitly extracts the wallet ID and return only items
    belongign to the wallet.

    Returns:
    ---------
    List of webhooks belonging to the wallet
    """
    return get_hooks_per_wallet(client=aries_controller)


@router.get("/{topic}")
async def get_webhooks_for_wallet_by_topic(
    topic: topics,
    aries_controller: AcaPyClient = Depends(agent_selector),
) -> List[TopicItem]:
    """
    Returns the webhooks per wallet per topic

    This implicitly extracts the wallet ID and return only items
    belongign to the wallet.

    Returns:
    ---------
    List of webhooks belonging to the wallet
    """
    return get_hooks_per_topic_per_wallet(client=aries_controller, topic=topic)
