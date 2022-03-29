import logging
from typing import List, Literal, Optional
import httpx
from fastapi.exceptions import HTTPException
from typing_extensions import TypedDict
from app.constants import TRUST_REGISTRY_URL

logger = logging.getLogger(__name__)

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
    and will also make sure the specified schema_id is regsitred as a valid schema.
    Raises an exception if one of the assertions fail.

    NOTE: the dids in the registry are registered as fully qualified dids. This means
    when passing a did to this method it must also be fully qualified (e.g. `did:sov:xxxx`)

    Args:
        did (str): the did of the issuer in fully qualified format.
        schema_id (str): the schema_id of the credential being issued

    Raises:
        Exception: When the did is not registered, the actor doesn't have the issuer role
            or the schema is not registered in the registry.
    """
    actor = await actor_by_did(did)

    if not actor:
        raise TrustRegistryException(f"Did {did} not registered in the trust registry")

    actor_id = actor["id"]
    if not "issuer" in actor["roles"]:
        raise TrustRegistryException(
            f"Actor {actor_id} does not have required role 'issuer'"
        )

    has_schema = await registry_has_schema(schema_id)
    if not has_schema:
        raise TrustRegistryException(
            f"Schema with id {schema_id} is not registered in trust registry"
        )


async def actor_has_role(actor_id: str, role: TrustRegistryRole) -> bool:
    """Check whether the actor has specified role.

    Args:
        actor_id (str): identifier of the actor to check the role for
        role (Role): role of the actor

    Returns:
        bool: Whether the actor with specified id has specified role
    """
    actor = await actor_by_id(actor_id)

    if not actor:
        raise TrustRegistryException(f"Actor with id {actor_id} not found", 404)

    return bool(role in actor["roles"])


async def actor_by_did(did: str) -> Optional[Actor]:
    """Retrieve actor by did from trust registry

    Args:
        actor_id (str): did of the actor to retrieve

    Raises:
        TrustRegistryException: If an error occurred while retrieving the actor.

    Returns:
        Actor: The actor with specified did.
    """
    actor_res = httpx.get(f"{TRUST_REGISTRY_URL}/registry/actors/did/{did}")

    if actor_res.status_code == 404:
        return None
    elif actor_res.is_error:
        raise TrustRegistryException(
            f"Error fetching actor by did: {actor_res.text}", actor_res.status_code
        )

    return actor_res.json()


async def actor_by_id(actor_id: str) -> Optional[Actor]:
    """Retrieve actor by id from trust registry

    Args:
        actor_id (str): Identifier of the actor to retrieve

    Raises:
        TrustRegistryException: If an error occurred while retrieving the actor.

    Returns:
        Actor: The actor with specified id.
    """
    actor_res = httpx.get(f"{TRUST_REGISTRY_URL}/registry/actors/{actor_id}")

    if actor_res.status_code == 404:
        return None
    elif actor_res.is_error:
        raise TrustRegistryException(
            f"Error fetching actor by id: {actor_res.text}", actor_res.status_code
        )

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
    actors_res = httpx.get(f"{TRUST_REGISTRY_URL}/registry/actors")

    if actors_res.is_error:
        raise TrustRegistryException(
            f"Unable to retrieve actors from registry: {actors_res.text}",
        )

    actors = actors_res.json()
    actors_with_role_list = [
        actor for actor in actors["actors"] if role in actor["roles"]
    ]

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
    schema_res = httpx.get(f"{TRUST_REGISTRY_URL}/registry/schemas")

    if schema_res.status_code == 404:
        return False
    elif schema_res.is_error:
        raise TrustRegistryException(
            f"Unable to retrieve schema {schema_id} from registry: {schema_res.text}",
            schema_res.status_code,
        )

    schema = schema_res.json()
    return bool(schema_id in schema["schemas"])


async def get_trust_registry_schemas() -> List:
    """Retrieve all schemas from the trust registry

    Raises:
        TrustRegistryException: If an error occurred while retrieving the trust registry schemas.

    Returns:
        A list of schemas
    """
    trust_registry_schemas_res = httpx.get(f"{TRUST_REGISTRY_URL}/registry/schemas")

    if trust_registry_schemas_res.is_error:
        raise TrustRegistryException(
            trust_registry_schemas_res.text, trust_registry_schemas_res.status_code
        )

    return trust_registry_schemas_res.json()["schemas"]


async def get_trust_registry() -> TrustRegistry:
    """Retrieve the complete trust registry

    Raises:
        TrustRegistryException: If an error occurred while retrieving the trust registry.

    Returns:
        TrustRegistry: the trust registries
    """
    trust_registry_res = httpx.get(f"{TRUST_REGISTRY_URL}/registry")

    if trust_registry_res.is_error:
        raise TrustRegistryException(
            trust_registry_res.text, trust_registry_res.status_code
        )

    return trust_registry_res.json()


async def register_schema(schema_id: str) -> None:
    """Register a schema in the trust registry

    Args:
        schema_id (str): the schema id to register

    Raises:
        TrustRegistryException: If an error ocurred while registering the schema
    """
    schema_res = httpx.post(
        f"{TRUST_REGISTRY_URL}/registry/schemas", json={"schema_id": schema_id}
    )

    if schema_res.is_error:
        raise TrustRegistryException(
            f"Error registering schema {schema_id}: {schema_res.text}",
            schema_res.status_code,
        )


async def register_actor(actor: Actor) -> None:
    """Register an actor in the trust registry

    Args:
        actor (Actor): the actor to register

    Raises:
        TrustRegistryException: If an error ocurred while registering the schema
    """
    actor_res = httpx.post(f"{TRUST_REGISTRY_URL}/registry/actors", json=actor)

    if actor_res.status_code == 422:
        raise TrustRegistryException(actor_res.json(), 422)
    if actor_res.is_error:
        raise TrustRegistryException(
            f"Error registering actor: {actor_res.text}", actor_res.status_code
        )


async def remove_actor_by_id(actor_id: str) -> None:
    """Remove actor from trust registry by id

    Args:
        actor_id (str): identifier of the actor to remove

    Raises:
        TrustRegistryException: If an error occurred while removing the actor
    """
    remove_response = httpx.delete(f"{TRUST_REGISTRY_URL}/registry/actors/{actor_id}")

    if remove_response.is_error:
        raise TrustRegistryException(
            f"Error removing actor from trust registry: {remove_response.text}",
            remove_response.status_code,
        )


async def remove_schema_by_id(schema_id: str) -> None:
    """Remove schema from trust registry by id

    Args:
        actor_id (str): identifier of the schema to remove

    Raises:
        TrustRegistryException: If an error occurred while removing the schema
    """
    remove_response = httpx.delete(f"{TRUST_REGISTRY_URL}/registry/schemas/{schema_id}")

    if remove_response.is_error:
        raise TrustRegistryException(
            f"Error removing schema from trust registry: {remove_response.text}",
            remove_response.status_code,
        )


async def update_actor(actor: Actor) -> None:
    actor_id = actor["id"]

    update_response = httpx.post(
        f"{TRUST_REGISTRY_URL}/registry/actors/{actor_id}", json=actor
    )

    if update_response.status_code == 422:
        raise TrustRegistryException(update_response.json(), 422)
    elif update_response.is_error:
        raise TrustRegistryException(
            f"Error updating actor in trust registry: {update_response.text}"
        )
