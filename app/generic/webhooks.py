import logging
from typing import Any, List

from fastapi import APIRouter, Depends

from app.dependencies.auth import AcaPyAuthVerified, acapy_auth_verified
from app.facades.webhooks import get_hooks_for_wallet, get_hooks_for_wallet_by_topic
from shared import CloudApiTopics, TopicItem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("")
async def get_webhooks_for_wallet(
    # Makes sure the authentication is verified
    auth: AcaPyAuthVerified = Depends(acapy_auth_verified),
) -> List[TopicItem[Any]]:
    """
    Returns all webhooks per wallet

    This implicitly extracts the wallet ID and return only items
    belonging to the wallet.

    Returns:
    ---------
    List of webhooks belonging to the wallet
    """

    return get_hooks_for_wallet(wallet_id=auth.wallet_id)


@router.get("/{topic}")
async def get_webhooks_for_wallet_by_topic(
    topic: CloudApiTopics,
    # Makes sure the authentication is verified
    auth: AcaPyAuthVerified = Depends(acapy_auth_verified),
) -> List[TopicItem[Any]]:
    """
    Returns the webhooks per wallet per topic

    This implicitly extracts the wallet ID and return only items
    belonging to the wallet.

    Returns:
    ---------
    List of webhooks belonging to the wallet
    """
    return get_hooks_for_wallet_by_topic(wallet_id=auth.wallet_id, topic=topic)
