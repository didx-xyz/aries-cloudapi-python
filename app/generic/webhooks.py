import logging
from typing import List, Union
from aries_cloudcontroller import AcaPyClient

from fastapi import APIRouter, Depends

from app.dependencies import agent_selector
from app.facades.webhooks import (
    get_hooks_per_topic_admin,
    get_hooks_per_topic_per_wallet,
    topics,
)
from app.generic.models import ProofsHook, ConnectionsHook, CredentialsHooks, TopicItem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("/{topic}")
async def get_webhooks_for_wallet_by_topic(
    topic: topics = "connections",
    aries_controller: AcaPyClient = Depends(agent_selector),
) -> List[Union[ProofsHook, ConnectionsHook, CredentialsHooks, TopicItem]]:
    """
    Returns the webhooks per wallet per topic

    This implicitly extracts the wallet ID and return only items
    belongign to the wallet.

    Returns:
    ---------
    List of webhooks belonging to the wallet
    """
    if not hasattr(aries_controller, "tenant_jwt"):
        hooks = get_hooks_per_topic_admin(client=aries_controller, topic=topic)
    else:
        hooks = get_hooks_per_topic_per_wallet(client=aries_controller, topic=topic)

    return hooks
