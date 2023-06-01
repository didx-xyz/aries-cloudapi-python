from typing import List

from httpx import HTTPError, get

from app.constants import WEBHOOKS_URL
from shared_models import CloudApiTopics


def get_hooks_per_topic_per_wallet(wallet_id: str, topic: CloudApiTopics) -> List:
    try:
        hooks = (get(f"{WEBHOOKS_URL}/{topic}/{wallet_id}")).json()
        return hooks if hooks else []
    except HTTPError as e:
        raise e from e


def get_hooks_per_wallet(wallet_id: str) -> List:
    """
    Gets all webhooks for all wallets by topic (default="connections")
    """
    try:

        hooks = (get(f"{WEBHOOKS_URL}/{wallet_id}")).json()
        # Only return the first 100 hooks to prevent OpenAPI interface from crashing
        return hooks if hooks else []
    except HTTPError as e:
        raise e from e
