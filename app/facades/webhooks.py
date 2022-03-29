from aries_cloudcontroller import AcaPyClient

from typing import List
from shared_models import CloudApiTopics
from httpx import get, HTTPError

from app.constants import WEBHOOKS_URL


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


def is_tenant(client: AcaPyClient):
    return "authorization" in client.client.headers
