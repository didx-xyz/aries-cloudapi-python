from typing import List

from httpx import HTTPError, get

from shared import WEBHOOKS_URL
from shared.log_config import get_logger
from shared.models.topics import CloudApiTopics

logger = get_logger(__name__)


def get_hooks_for_wallet_by_topic(wallet_id: str, topic: CloudApiTopics) -> List:
    bound_logger = logger.bind(body={"wallet_id": wallet_id, "topic": topic})
    bound_logger.info("Fetching webhooks events from /webhooks/wallet_id/topic")
    try:
        hooks = (get(f"{WEBHOOKS_URL}/webhooks/{wallet_id}/{topic}")).json()
        return hooks if hooks else []
    except HTTPError as e:
        bound_logger.exception("HTTP Error caught when fetching webhooks.")
        raise e from e


def get_hooks_for_wallet(wallet_id: str) -> List:
    """
    Gets webhooks for wallet. Only return the first 100 hooks to not overload OpenAPI interface
    """
    bound_logger = logger.bind(body={"wallet_id": wallet_id})
    bound_logger.info("Fetching webhooks events from /webhooks/wallet_id")
    try:
        hooks = (get(f"{WEBHOOKS_URL}/webhooks/{wallet_id}")).json()
        return hooks if hooks else []
    except HTTPError as e:
        bound_logger.exception("HTTP Error caught when fetching webhooks.")
        raise e from e
