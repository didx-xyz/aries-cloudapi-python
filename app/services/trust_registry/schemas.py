from typing import List

from app.exceptions.trust_registry_exception import TrustRegistryException
from app.models.trust_registry import Schema
from shared.constants import TRUST_REGISTRY_URL
from shared.log_config import get_logger
from shared.util.rich_async_client import RichAsyncClient

logger = get_logger(__name__)


async def get_trust_registry_schemas() -> List[Schema]:
    """Retrieve all schemas from the trust registry

    Raises:
        TrustRegistryException: If an error occurred while retrieving the trust registry schemas.

    Returns:
        A list of schemas
    """
    logger.info("Fetching all schemas from trust registry")
    async with RichAsyncClient(raise_status_error=False) as client:
        schemas_res = await client.get(f"{TRUST_REGISTRY_URL}/registry/schemas")

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


async def register_schema(schema_id: str) -> None:
    """Register a schema in the trust registry

    Args:
        schema_id (str): the schema id to register

    Raises:
        TrustRegistryException: If an error ocurred while registering the schema
    """
    bound_logger = logger.bind(body={"schema_id": schema_id})
    bound_logger.info("Registering schema on trust registry")
    async with RichAsyncClient(raise_status_error=False) as client:
        schema_res = await client.post(
            f"{TRUST_REGISTRY_URL}/registry/schemas", json={"schema_id": schema_id}
        )

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


async def remove_schema_by_id(schema_id: str) -> None:
    """Remove schema from trust registry by id

    Args:
        actor_id (str): identifier of the schema to remove

    Raises:
        TrustRegistryException: If an error occurred while removing the schema
    """
    bound_logger = logger.bind(body={"schema_id": schema_id})
    bound_logger.info("Removing schema from trust registry")
    async with RichAsyncClient(raise_status_error=False) as client:
        remove_response = await client.delete(
            f"{TRUST_REGISTRY_URL}/registry/schemas/{schema_id}"
        )

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


async def get_schema_by_id(schema_id: str) -> Schema:
    """Retrieve a schemas from the trust registry

    Raises:
        TrustRegistryException: If an error occurred while retrieving the trust registry schemas.

    Returns:
        A schema
    """
    bound_logger = logger.bind(body={"schema_id": schema_id})
    bound_logger.info("Fetching schema from trust registry")

    try:
        async with httpx.AsyncClient() as client:
            schema_response = await client.get(
                f"{TRUST_REGISTRY_URL}/registry/schemas/{schema_id}"
            )
    except httpx.HTTPError as e:
        logger.exception("HTTP Error caught when fetching from trust registry.")
        raise e

    if schema_response.status_code == 404:
        bound_logger.info("Bad request: Schema not found.")
        return None
    if schema_response.is_error:
        logger.error(
            "Error fetching schema. Got status code {} with message `{}`.",
            schema_response.status_code,
            schema_response.text,
        )
        raise TrustRegistryException(
            f"Unable to fetch schema: `{schema_response.text}`.",
            schema_response.status_code,
        )

    result = schema_response.json()
    logger.info("Successfully fetched schema from trust registry.")
    return result
