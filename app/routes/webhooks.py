from typing import List

from fastapi import APIRouter, Depends

from app.dependencies.auth import AcaPyAuthVerified, acapy_auth_verified
from app.services.webhooks import get_hooks_for_wallet, get_hooks_for_wallet_by_topic
from shared.log_config import get_logger
from shared.models.webhook_events import CloudApiTopics, CloudApiWebhookEventGeneric

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])


@router.get("", deprecated=True)
async def get_webhooks_for_wallet(
    auth: AcaPyAuthVerified = Depends(acapy_auth_verified),
) -> List[CloudApiWebhookEventGeneric]:
    """
    **Deprecated**: Fetching bulk webhook events is set to be removed.
    We recommend monitoring webhook events live, using the SSE endpoint instead, or websockets if preferred.

    Returns 100 most recent webhooks for this wallet

    This implicitly extracts the wallet ID and return only items
    belonging to the caller's wallet.

    Returns:
    ---------
    List of webhooks belonging to the wallet
    """
    logger.bind(body={"wallet_id": auth.wallet_id}).info(
        "GET request received: Get webhooks for wallet"
    )

    return await get_hooks_for_wallet(wallet_id=auth.wallet_id)


@router.get("/{topic}", deprecated=True)
async def get_webhooks_for_wallet_by_topic(
    topic: CloudApiTopics,
    auth: AcaPyAuthVerified = Depends(acapy_auth_verified),
) -> List[CloudApiWebhookEventGeneric]:
    """
    **Deprecated**: Fetching bulk webhook events is set to be removed.
    We recommend monitoring webhook events live, using the SSE endpoint instead, or websockets if preferred.

    Returns 100 most recent webhooks for this wallet / topic pair

    This implicitly extracts the wallet ID and return only items
    belonging to the caller's wallet.

    Returns:
    ---------
    List of webhooks belonging to the wallet
    """
    logger.bind(body={"wallet_id": auth.wallet_id, "topic": topic}).info(
        "GET request received: Get webhooks for wallet by topic"
    )

    return await get_hooks_for_wallet_by_topic(wallet_id=auth.wallet_id, topic=topic)
