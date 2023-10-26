from typing import List, Optional

from fastapi import APIRouter, HTTPException

import app.services.trust_registry.actors as registry_actors
import app.services.trust_registry.schemas as registry_schemas
from app.models.trust_registry import Actor, Schema
from shared.log_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/trust-registry", tags=["trust-registry"])


@router.get("/schemas", response_model=List[Schema])
async def get_schemas() -> List[Schema]:
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
async def get_schema_by_id(schema_id: str) -> Schema:
    """
    Retrieve schema by id.

    Parameters:
    -----------
    schema_id: str

    Returns:
    -----------
    A schema from the trust registry
    """
    bound_logger = logger.bind(body={"schema_id": schema_id})
    bound_logger.info("GET request received: Fetch schema by id")
    schema = await registry_schemas.get_schema_by_id(schema_id)

    if schema:
        bound_logger.info("Successfully fetched schema by id.")
        return schema
    else:
        bound_logger.info("Bad request: schema not found.")
        raise HTTPException(404, f"Schema with id: {schema_id} not found")


@router.get("/actors", response_model=List[Actor])
async def get_actors(
    actor_did: Optional[str] = None,
    actor_name: Optional[str] = None,
    actor_id: Optional[str] = None,
) -> List[Actor]:
    """
    Get all actors from the trust registry.
    Alternatively, provide one of: did, name, or id, to fetch corresponding actor

    Parameters:
    -----------
    actor_did: str (Optional)
    actor_name: str (Optional)
    actor_id: str (Optional)

    Returns:
    ---------
    All actors from the trust registry, or one actor if a query parameter is passed
    """
    param_count = sum(1 for var in [actor_did, actor_name, actor_id] if var)

    if param_count == 0:
        logger.info("GET request received: Fetch all actors from the trust registry")
        actors = await registry_actors.all_actors()

        logger.info("Successfully retrieved actors.")
        return actors

    bound_logger = logger.bind(
        body={"actor_did": actor_did, "actor_id": actor_id, "actor_name": actor_name}
    )
    bound_logger.info("GET request received: Fetch actor by query param")

    if param_count > 1:
        bound_logger.info("Bad request, more than one query param provided.")
        raise HTTPException(
            400,
            "Bad request: More than one query parameter provided when max 1 expected",
        )

    # One query param provided:
    if actor_did:
        bound_logger.info(
            "GET request received: Fetch actor by did from the trust registry"
        )
        actor = await registry_actors.actor_by_did(actor_did)
    elif actor_id:
        bound_logger.info(
            "GET request received: Fetch actor by id from the trust registry"
        )
        actor = await registry_actors.actor_by_id(actor_id)
    elif actor_name:
        bound_logger.info(
            "GET request received: Fetch actor by name from the trust registry"
        )
        actor = await registry_actors.actor_by_name(actor_name)

    if actor:
        bound_logger.info("Successfully retrieved actor.")
        return [actor]
    else:
        bound_logger.info("Bad request: actor not found.")
        raise HTTPException(404, "Actor not found")


@router.get("/actors/issuers", response_model=List[Actor])
async def get_issuers() -> List[Actor]:
    """
    Get the issuers from the trust registry.

    Returns:
    ---------
    List of actor models, representing the issuers from the trust registry
    """
    logger.info("GET request received: Get only the issuers from the trust registry")
    issuers = await registry_actors.actors_with_role("issuer")

    logger.info("Successfully retrieved issuers.")
    return issuers


@router.get("/actors/verifiers", response_model=List[Actor])
async def get_verifiers() -> List[Actor]:
    """
    Get the verifiers from the trust registry.

    Returns:
    ---------
    List of actor models, representing the verifiers from the trust registry
    """
    logger.info("GET request received: Get only the verifiers from the trust registry")
    verifiers = await registry_actors.actors_with_role("verifier")

    logger.info("Successfully retrieved verifiers.")
    return verifiers
