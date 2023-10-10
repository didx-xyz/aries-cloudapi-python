from typing import List, Optional

from app.exceptions.trust_registry_exception import TrustRegistryException
from app.models.trust_registry import Actor, TrustRegistryRole
from shared.constants import TRUST_REGISTRY_URL
from shared.log_config import get_logger
from shared.util.rich_async_client import RichAsyncClient

logger = get_logger(__name__)


async def register_actor(actor: Actor) -> None:
    """Register an actor in the trust registry

    Args:
        actor (Actor): the actor to register

    Raises:
        TrustRegistryException: If an error ocurred while registering the schema
    """
    bound_logger = logger.bind(body={"actor": actor})
    bound_logger.info("Registering actor on trust registry")
    async with RichAsyncClient(raise_status_error=False) as client:
        actor_res = await client.post(
            f"{TRUST_REGISTRY_URL}/registry/actors", json=actor
        )

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


async def update_actor(actor: Actor) -> None:
    bound_logger = logger.bind(body={"actor": actor})
    bound_logger.info("Updating actor on trust registry")
    async with RichAsyncClient(raise_status_error=False) as client:
        update_response = await client.put(
            f"{TRUST_REGISTRY_URL}/registry/actors/{actor['id']}", json=actor
        )

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
    async with RichAsyncClient(raise_status_error=False) as client:
        actor_res = await client.get(f"{TRUST_REGISTRY_URL}/registry/actors/did/{did}")

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
    async with RichAsyncClient(raise_status_error=False) as client:
        actor_res = await client.get(f"{TRUST_REGISTRY_URL}/registry/actors/{actor_id}")

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
    async with RichAsyncClient(raise_status_error=False) as client:
        actors_res = await client.get(f"{TRUST_REGISTRY_URL}/registry/actors")

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


async def remove_actor_by_id(actor_id: str) -> None:
    """Remove actor from trust registry by id

    Args:
        actor_id (str): identifier of the actor to remove

    Raises:
        TrustRegistryException: If an error occurred while removing the actor
    """
    bound_logger = logger.bind(body={"actor_id": actor_id})
    bound_logger.info("Removing actor from trust registry")
    async with RichAsyncClient(raise_status_error=False) as client:
        remove_response = await client.delete(
            f"{TRUST_REGISTRY_URL}/registry/actors/{actor_id}"
        )

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
