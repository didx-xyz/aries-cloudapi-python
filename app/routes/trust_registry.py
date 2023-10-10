from fastapi import APIRouter

import app.services.trust_registry as trust_registry_facade
from shared.log_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/trust-registry", tags=["trust-registry"])


@router.get("/schemas", response_model=trust_registry_facade.Schemas)
async def get_schemas():
    """
    Get only the schemas from the trust registry.

    Returns:
    ---------
    Only the schemas from the trust registry
    """
    logger.info("GET request received: Get only the schemas from the trust registry")
    schemas = await trust_registry_facade.get_schemas()

    logger.info("Successfully retrieved schemas.")
    return schemas


@router.get("/actors", response_model=trust_registry_facade.Actors)
async def get_actors():
    """
    Get all actors from the trust registry.

    Returns:
    ---------
    All actors from the trust registry
    """
    logger.info("GET request received: Get all actors from the trust registry")
    actors = await trust_registry_facade.get_actors()

    logger.info("Successfully retrieved actors.")
    return actors


@router.get("/actors/issuers", response_model=trust_registry_facade.Issuers)
async def get_issuers():
    """
    Get only the issuers from the trust registry.

    Returns:
    ---------
    Only the issuers from the trust registry
    """
    logger.info("GET request received: Get only the issuers from the trust registry")
    issuers = await trust_registry_facade.get_issuers()

    logger.info("Successfully retrieved issuers.")
    return issuers


@router.get("/actors/verifiers", response_model=trust_registry_facade.Verifiers)
async def get_verifiers():
    """
    Get only the verifiers from the trust registry.

    Returns:
    ---------
    Only the verifiers from the trust registry
    """
    logger.info("GET request received: Get only the verifiers from the trust registry")
    verifiers = await trust_registry_facade.get_verifiers()

    logger.info("Successfully retrieved verifiers.")
    return verifiers
