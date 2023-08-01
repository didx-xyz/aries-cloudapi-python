from fastapi import APIRouter

import app.services.trust_registry as trust_registry_facade
from shared.log_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/trust-registry", tags=["trust-registry"])


@router.get("", response_model=trust_registry_facade.TrustRegistry)
async def get_trust_registry():
    """
    Get the trust registry.

    Returns:
    ---------
    The trust registry with actors and schemas
    """
    logger.info("GET request received: Get the complete trust registry")
    trust_registry = await trust_registry_facade.get_trust_registry()

    logger.info("Successfully retrieved trust registry.")
    return trust_registry
