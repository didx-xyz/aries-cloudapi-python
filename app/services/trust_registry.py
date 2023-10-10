from typing import List, Optional

import httpx

from app.exceptions.trust_registry_exception import TrustRegistryException
from shared.constants import TRUST_REGISTRY_URL
from shared.log_config import get_logger
from shared.util.rich_async_client import RichAsyncClient

logger = get_logger(__name__)


async def assert_valid_issuer(did: str, schema_id: Optional[str] = None):
    """Assert that an actor with the specified did is registered as issuer.

    This method asserts that there is an actor registered in the trust registry
    with the specified did. It verifies whether this actor has the `issuer` role
    and will also make sure the specified schema_id is registered as a valid schema.
    Raises an exception if one of the assertions fail.

    NOTE: the dids in the registry are registered as fully qualified dids. This means
    when passing a did to this method it must also be fully qualified (e.g. `did:sov:xxxx`)

    Args:
        did (str): the did of the issuer in fully qualified format.
        schema_id (Optional[str]): the schema_id of the credential being issued (Optional).

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
    bound_logger.info("Issuer DID is valid")

    if schema_id:
        has_schema = await registry_has_schema(schema_id)
        if not has_schema:
            bound_logger.info("Schema is not registered in the trust registry.")
            raise TrustRegistryException(
                f"Schema with id {schema_id} is not registered in trust registry."
            )
        bound_logger.info("Schema ID is registered.")


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
        async with RichAsyncClient(raise_status_error=False) as client:
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
