from typing import List

from fastapi import APIRouter, HTTPException

import app.services.trust_registry.actors as registry_actors
import app.services.trust_registry.schemas as registry_schemas
from app.models.trust_registry import Actor, Schema
from shared.log_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/trust-registry", tags=["trust-registry"])


@router.get("/schemas", response_model=List[str])
async def get_schemas():
    """
    Get only the schemas from the trust registry.

    Returns:
    ---------
    Only the schemas from the trust registry
    """
    logger.info("GET request received: Get only the schemas from the trust registry")
    schemas = await registry_schemas.get_trust_registry_schemas()

    logger.info("Successfully retrieved schemas.")
    return schemas


@router.get("/schemas/{schema_id}", response_model=Schema)
async def get_schema_by_id(schema_id:str):
    """
    Retrieve schema by id.

    Parameters:
    -----------
    schema_id: str

    Returns:
    -----------
    A schema from the trust registry
    """
    logger.info("GET request received: Get schema by id from the trust registry")
    schema = await registry_schemas.get_schema_by_id(schema_id)

    if schema is not None:
        logger.info("Successfully retrieved schema.")
        return schema
    else:
        raise HTTPException(404, f"Schema with id: {schema_id} not found")
    
    
@router.get("/actors", response_model=List[Actor])
async def get_actors(
    actor_did: str = None,
    actor_name: str = None,
    actor_id: str = None
):
    """
    Get all actors from the trust registry.

    Returns:
    ---------
    All actors from the trust registry
    """
    logger.info("GET request received: Get all actors from the trust registry")
    actors = await registry_actors.actors_with_role("")

    logger.info("Successfully retrieved actors.")
    return actors


@router.get("/actors/issuers", response_model=List[Actor])
async def get_issuers():
    """
    Get only the issuers from the trust registry.

    Returns:
    ---------
    List of actor models, representing the issuers from the trust registry
    """
    logger.info("GET request received: Get only the issuers from the trust registry")
    issuers = await registry_actors.actors_with_role("issuer")

    logger.info("Successfully retrieved issuers.")
    return issuers


@router.get("/actors/verifiers", response_model=List[Actor])
async def get_verifiers():
    """
    Get only the verifiers from the trust registry.

    Returns:
    ---------
    List of actor models, representing only the verifiers from the trust registry
    """
    logger.info("GET request received: Get only the verifiers from the trust registry")
    verifiers = await registry_actors.actors_with_role("verifier")

    logger.info("Successfully retrieved verifiers.")
    return verifiers
