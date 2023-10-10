from typing import List, Optional

import httpx

from app.exceptions.trust_registry_exception import TrustRegistryException
from shared.constants import TRUST_REGISTRY_URL
from shared.log_config import get_logger
from shared.util.rich_async_client import RichAsyncClient

logger = get_logger(__name__)


async def get_trust_registry() -> TrustRegistry:
    """Retrieve the complete trust registry

    Raises:
        TrustRegistryException: If an error occurred while retrieving the trust registry.

    Returns:
        TrustRegistry: the trust registries
    """
    logger.info("Fetching complete trust registry")
    try:
        async with RichAsyncClient(raise_status_error=False) as client:
            trust_registry_res = await client.get(f"{TRUST_REGISTRY_URL}/registry")
    except httpx.HTTPError as e:
        logger.exception("HTTP Error caught when fetching trust registry.")
        raise e from e

    if trust_registry_res.is_error:
        logger.error(
            "Error fetching trust registry. Got status code {} with message `{}`.",
            trust_registry_res.status_code,
            trust_registry_res.text,
        )
        raise TrustRegistryException(
            f"Error fetching registry: `{trust_registry_res.text}`.",
            trust_registry_res.status_code,
        )

    result = trust_registry_res.json()
    logger.info("Successfully fetched complete trust registry.")
    return result
