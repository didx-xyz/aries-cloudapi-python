from typing import List, Literal, Optional

import httpx
from fastapi.exceptions import HTTPException
from typing_extensions import TypedDict

from shared.constants import TRUST_REGISTRY_URL
from shared.log_config import get_logger

logger = get_logger(__name__)

TrustRegistryRole = Literal["issuer", "verifier"]


class TrustRegistryException(HTTPException):
    """Class that represents a trust registry error"""

    def __init__(
        self,
        detail: str,
        status_code: int = 403,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail)


class Actor(TypedDict):
    id: str
    name: str
    roles: List[TrustRegistryRole]
    did: str
    didcomm_invitation: Optional[str]


class TrustRegistry(TypedDict):
    actors: List[Actor]
    schemas: List[str]


async def assert_valid_issuer(did: str, schema_id: str):
    """Assert that an actor with the specified did is registered as issuer.

    This method asserts that there is an actor registered in the trust registry
    with the specified did. It verifies whether this actor has the `issuer` role
    and will also make sure the specified schema_id is registered as a valid schema.
    Raises an exception if one of the assertions fail.

    NOTE: the dids in the registry are registered as fully qualified dids. This means
    when passing a did to this method it must also be fully qualified (e.g. `did:sov:xxxx`)

    Args:
        did (str): the did of the issuer in fully qualified format.
        schema_id (str): the schema_id of the credential being issued.

    Raises:
        Exception: When the did is not registered, the actor doesn't have the issuer role
            or the schema is not registered in the registry.
    """
    bound_logger = logger.bind(body={"did": did, "schema_id": schema_id})
    bound_logger.info("Asserting issuer DID and schema_id is registered")
    actor = await actor_by_did(did)

    if not actor:
        bound_logger.info("DID not registered in the trust registry.")
        raise TrustRegistryException(f"DID {did} not registered in the trust registry.")

    if "issuer" not in actor["roles"]:
        bound_logger.info("Actor associated with DID does not have `issuer` role.")
        raise TrustRegistryException(
            f"Actor {actor['id']} does not have required role 'issuer'."
        )

    has_schema = await registry_has_schema(schema_id)
    if not has_schema:
        bound_logger.info("Schema is not registered in the trust registry.")
        raise TrustRegistryException(
            f"Schema with id {schema_id} is not registered in trust registry."
        )
    bound_logger.info("Issuer DID and schema ID is valid.")


async def actor_has_role(actor_id: str, role: TrustRegistryRole) -> bool:
    """Check whether the actor has specified role.

    Args:
        actor_id (str): identifier of the actor to check the role for
        role (Role): role of the actor

    Returns:
        bool: Whether the actor with specified id has specified role
    """
    bound_logger = logger.bind(body={"actor_id": actor_id, "role": role})
    bound_logger.info("Asserting actor has role")
    actor = await actor_by_id(actor_id)

    if not actor:
        bound_logger.info("Actor not registered in trust registry.")
        raise TrustRegistryException(f"Actor with id {actor_id} not found.", 404)

    result = bool(role in actor["roles"])
    if result:
        bound_logger.info("Actor has requested role.")
    else:
        bound_logger.info("Actor does not have requested role.")
    return result


async def actor_by_did(did: str) -> Optional[Actor]:
    """Retrieve actor by did from trust registry

    Args:
        actor_id (str): did of the actor to retrieve

    Raises:
        TrustRegistryException: If an error occurred while retrieving the actor.

    Returns:
        Actor: The actor with specified did.
    """
    bound_logger = logger.bind(body={"did": did})
    bound_logger.info("Fetching actor by DID from trust registry")
    try:
        async with httpx.AsyncClient() as client:
            actor_res = await client.get(
                f"{TRUST_REGISTRY_URL}/registry/actors/did/{did}"
            )
    except httpx.HTTPError as e:
        bound_logger.exception("HTTP Error caught when fetching from trust registry.")
        raise e from e

    if actor_res.status_code == 404:
        bound_logger.info("Bad request: actor not found.")
        return None
    elif actor_res.is_error:
        bound_logger.error(
            "Error fetching actor by DID. Got status code {} with message `{}`.",
            actor_res.status_code,
            actor_res.text,
        )
        raise TrustRegistryException(
            f"Error fetching actor by DID: `{actor_res.text}`.", actor_res.status_code
        )

    bound_logger.info("Successfully fetched actor from trust registry.")
    return actor_res.json()


async def actor_by_name(actor_name: str) -> Optional[Actor]:
    """Retrieve actor by name from trust registry

    Args:
        actor_name (str): name of the actor to retrieve

    Raises:
        TrustRegistryException: If an error occurred while retrieving the actor.

    Returns:
        Actor: The actor with specified name.
    """
    bound_logger = logger.bind(body={"actor_name": actor_name})
    bound_logger.info("Fetching actor by name from trust registry")

    try:
        async with httpx.AsyncClient() as client:
            actor_response = await client.get(
                f"{TRUST_REGISTRY_URL}/registry/actors/{actor_name}"
            )
    except HTTPException as e:
        bound_logger.exception("HTTP Error caught when fetching from trust registry.")
        bound_logger.info("======>{}", e)
        raise e from e

    if actor_response.status_code == 404:
        bound_logger.info("Bad request: actor not found")
        raise HTTPException(status_code=404, detail="Actor not found.")

    elif actor_response.is_error:
        bound_logger.error(
            "Error fetching actor by id. Got status code {} with message `{}`.",
            actor_response.status_code,
            actor_response.text,
        )
        raise TrustRegistryException(
            f"Error fetching actor by name: `{actor_response.text}`",
            actor_response.status_code,
        )

    bound_logger.info("Successfully fetched actor from trust registry.")
    return actor_response.json()


async def actor_by_id(actor_id: str) -> Optional[Actor]:
    """Retrieve actor by id from trust registry

    Args:
        actor_id (str): Identifier of the actor to retrieve

    Raises:
        TrustRegistryException: If an error occurred while retrieving the actor.

    Returns:
        Actor: The actor with specified id.
    """
    bound_logger = logger.bind(body={"actor_id": actor_id})
    bound_logger.info("Fetching actor by ID from trust registry")
    try:
        async with httpx.AsyncClient() as client:
            actor_res = await client.get(
                f"{TRUST_REGISTRY_URL}/registry/actors/{actor_id}"
            )
    except httpx.HTTPError as e:
        bound_logger.exception("HTTP Error caught when fetching from trust registry.")
        raise e from e

    if actor_res.status_code == 404:
        bound_logger.info("Bad request: actor not found.")
        return None
    elif actor_res.is_error:
        bound_logger.error(
            "Error fetching actor by id. Got status code {} with message `{}`.",
            actor_res.status_code,
            actor_res.text,
        )
        raise TrustRegistryException(
            f"Error fetching actor by id: `{actor_res.text}`.", actor_res.status_code
        )

    bound_logger.info("Successfully fetched actor from trust registry.")
    return actor_res.json()


async def actors_with_role(role: TrustRegistryRole) -> List[Actor]:
    """Get all actors from the trust registry by role

    Args:
        role (Role): The role to filter actors by

    Raises:
        TrustRegistryException: If an error occurred while retrieving the actors

    Returns:
        List[Actor]: List of actors with specified role
    """
    bound_logger = logger.bind(body={"role": role})
    bound_logger.info("Fetching all actors with requested role from trust registry")
    try:
        async with httpx.AsyncClient() as client:
            actors_res = await client.get(f"{TRUST_REGISTRY_URL}/registry/actors")
    except httpx.HTTPError as e:
        bound_logger.exception("HTTP Error caught when fetching from trust registry.")
        raise e from e

    if actors_res.is_error:
        bound_logger.error(
            "Error fetching actors by role. Got status code {} with message `{}`.",
            actors_res.status_code,
            actors_res.text,
        )
        raise TrustRegistryException(
            f"Unable to retrieve actors from registry: `{actors_res.text}`.",
            actors_res.status_code,
        )

    actors = actors_res.json()
    actors_with_role_list = [
        actor for actor in actors["actors"] if role in actor["roles"]
    ]

    if actors_with_role_list:
        bound_logger.info("Successfully got actors with requested role.")
    else:
        bound_logger.info("No actors found with requested role.")

    return actors_with_role_list


async def registry_has_schema(schema_id: str) -> bool:
    """Check whether the trust registry has a schema registered

    Args:
        schema_id (str): the schema id to check

    Raises:
        TrustRegistryException: If an error occurred while retrieving the schemas

    Returns:
        bool: whether the schema exists in the trust registry
    """
    bound_logger = logger.bind(body={"schema_id": schema_id})
    bound_logger.info(
        "Asserting if schema is registered. Fetching schema by ID from trust registry"
    )
    try:
        async with httpx.AsyncClient() as client:
            bound_logger.debug("Fetch schema from trust registry")
            schema_res = await client.get(
                f"{TRUST_REGISTRY_URL}/registry/schemas/{schema_id}"
            )
            schema_res.raise_for_status()
    except httpx.HTTPStatusError as http_err:
        if http_err.response.status_code == 404:
            bound_logger.info("Schema id not registered in trust registry.")
            return False
        else:
            bound_logger.exception(
                "Something went wrong when fetching schema from trust registry."
            )
            raise http_err

    bound_logger.info("Schema exists in registry.")
    return True


async def get_trust_registry_schemas() -> List[str]:
    """Retrieve all schemas from the trust registry

    Raises:
        TrustRegistryException: If an error occurred while retrieving the trust registry schemas.

    Returns:
        A list of schemas
    """
    logger.info("Fetching all schemas from trust registry")
    try:
        async with httpx.AsyncClient() as client:
            schemas_res = await client.get(f"{TRUST_REGISTRY_URL}/registry/schemas")
    except httpx.HTTPError as e:
        logger.exception("HTTP Error caught when fetching from trust registry.")
        raise e from e

    if schemas_res.is_error:
        logger.error(
            "Error fetching schemas. Got status code {} with message `{}`.",
            schemas_res.status_code,
            schemas_res.text,
        )
        raise TrustRegistryException(
            f"Unable to fetch schemas: `{schemas_res.text}`.", schemas_res.status_code
        )

    result = schemas_res.json()["schemas"]
    logger.info("Successfully fetched schemas from trust registry.")
    return result


async def get_trust_registry() -> TrustRegistry:
    """Retrieve the complete trust registry

    Raises:
        TrustRegistryException: If an error occurred while retrieving the trust registry.

    Returns:
        TrustRegistry: the trust registries
    """
    logger.info("Fetching complete trust registry")
    try:
        async with httpx.AsyncClient() as client:
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


async def register_schema(schema_id: str) -> None:
    """Register a schema in the trust registry

    Args:
        schema_id (str): the schema id to register

    Raises:
        TrustRegistryException: If an error ocurred while registering the schema
    """
    bound_logger = logger.bind(body={"schema_id": schema_id})
    bound_logger.info("Registering schema on trust registry")
    try:
        async with httpx.AsyncClient() as client:
            schema_res = await client.post(
                f"{TRUST_REGISTRY_URL}/registry/schemas", json={"schema_id": schema_id}
            )
    except httpx.HTTPError as e:
        bound_logger.exception("HTTP Error caught when registering schema.")
        raise e from e

    if schema_res.is_error:
        bound_logger.error(
            "Error registering schema. Got status code {} with message `{}`.",
            schema_res.status_code,
            schema_res.text,
        )
        raise TrustRegistryException(
            f"Error registering schema `{schema_id}`. Error: `{schema_res.text}`.",
            schema_res.status_code,
        )

    bound_logger.info("Successfully registered schema on trust registry.")


async def register_actor(actor: Actor) -> None:
    """Register an actor in the trust registry

    Args:
        actor (Actor): the actor to register

    Raises:
        TrustRegistryException: If an error ocurred while registering the schema
    """
    bound_logger = logger.bind(body={"actor": actor})
    bound_logger.info("Registering actor on trust registry")
    try:
        async with httpx.AsyncClient() as client:
            actor_res = await client.post(
                f"{TRUST_REGISTRY_URL}/registry/actors", json=actor
            )
    except httpx.HTTPError as e:
        bound_logger.exception("HTTP Error caught when registering actor.")
        raise e from e

    if actor_res.status_code == 422:
        bound_logger.error(
            "Unprocessable entity response when registering actor: `{}`.",
            actor_res.json(),
        )
        raise TrustRegistryException(
            f"Unprocessable response when registering actor: `{actor_res.json()}`.", 422
        )
    if actor_res.is_error:
        bound_logger.error(
            "Error registering actor. Got status code {} with message `{}`.",
            actor_res.status_code,
            actor_res.text,
        )
        raise TrustRegistryException(
            f"Error registering actor: `{actor_res.text}`.", actor_res.status_code
        )

    bound_logger.info("Successfully registered actor on trust registry.")


async def remove_actor_by_id(actor_id: str) -> None:
    """Remove actor from trust registry by id

    Args:
        actor_id (str): identifier of the actor to remove

    Raises:
        TrustRegistryException: If an error occurred while removing the actor
    """
    bound_logger = logger.bind(body={"actor_id": actor_id})
    bound_logger.info("Removing actor from trust registry")
    try:
        async with httpx.AsyncClient() as client:
            remove_response = await client.delete(
                f"{TRUST_REGISTRY_URL}/registry/actors/{actor_id}"
            )
    except httpx.HTTPError as e:
        bound_logger.exception("HTTP Error caught when removing actor.")
        raise e from e

    if remove_response.status_code == 404:
        bound_logger.info(
            "Bad request: Tried to remove actor by id, but not found in registry."
        )
        return None
    if remove_response.is_error:
        bound_logger.error(
            "Error removing actor. Got status code {} with message `{}`.",
            remove_response.status_code,
            remove_response.text,
        )
        raise TrustRegistryException(
            f"Error removing actor from trust registry: `{remove_response.text}`.",
            remove_response.status_code,
        )

    bound_logger.info("Successfully removed actor from trust registry.")


async def remove_schema_by_id(schema_id: str) -> None:
    """Remove schema from trust registry by id

    Args:
        actor_id (str): identifier of the schema to remove

    Raises:
        TrustRegistryException: If an error occurred while removing the schema
    """
    bound_logger = logger.bind(body={"schema_id": schema_id})
    bound_logger.info("Removing schema from trust registry")
    try:
        async with httpx.AsyncClient() as client:
            remove_response = await client.delete(
                f"{TRUST_REGISTRY_URL}/registry/schemas/{schema_id}"
            )
    except httpx.HTTPError as e:
        bound_logger.exception("HTTP Error caught when removing schema.")
        raise e from e

    if remove_response.is_error:
        bound_logger.error(
            "Error removing schema. Got status code {} with message `{}`.",
            remove_response.status_code,
            remove_response.text,
        )
        raise TrustRegistryException(
            f"Error removing schema from trust registry: `{remove_response.text}`.",
            remove_response.status_code,
        )

    bound_logger.info("Successfully removed schema from trust registry.")


async def update_actor(actor: Actor) -> None:
    bound_logger = logger.bind(body={"actor": actor})
    bound_logger.info("Updating actor on trust registry")
    try:
        async with httpx.AsyncClient() as client:
            update_response = await client.put(
                f"{TRUST_REGISTRY_URL}/registry/actors/{actor['id']}", json=actor
            )
    except httpx.HTTPError as e:
        bound_logger.exception("HTTP Error caught when updating actor.")
        raise e from e

    if update_response.status_code == 422:
        bound_logger.error(
            "Unprocessable entity response when updating actor: `{}`.",
            update_response.json(),
        )
        raise TrustRegistryException(
            f"Unprocessable response when updating actor: `{update_response.json()}`.",
            422,
        )
    elif update_response.is_error:
        bound_logger.error(
            "Error removing actor. Got status code `{}` with message `{}`.",
            update_response.status_code,
            update_response.text,
        )
        raise TrustRegistryException(
            f"Error updating actor in trust registry: `{update_response.text}`.",
            update_response.status_code,
        )
