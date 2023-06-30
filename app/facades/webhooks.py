from typing import List

from httpx import HTTPError, get

from app.config.log_config import get_logger
from shared import WEBHOOKS_URL, CloudApiTopics

logger = get_logger(__name__)


def get_hooks_for_wallet_by_topic(wallet_id: str, topic: CloudApiTopics) -> List:
    try:
        hooks = (get(f"{WEBHOOKS_URL}/webhooks/{wallet_id}/{topic}")).json()
        return hooks if hooks else []
    except HTTPError as e:
        raise e from e


def get_hooks_for_wallet(wallet_id: str) -> List:
    """
    Gets webhooks for wallet. Only return the first 100 hooks to not overload OpenAPI interface
    """
    try:
        hooks = (get(f"{WEBHOOKS_URL}/webhooks/{wallet_id}")).json()
        return hooks if hooks else []
    except HTTPError as e:
        raise e from e
