import logging
from fastapi import APIRouter

import app.facades.trust_registry as trust_registry_facade

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trust-registry", tags=["trust registry"])

@router.get("", response_model=trust_registry_facade.TrustRegistry)
async def get_trust_registry():
    """
    Get the trust registry.

    Returns:
    ---------
    The trust registry with actors and schemas
    """
    trust_registry = await trust_registry_facade.get_trust_registry()

    return trust_registry
