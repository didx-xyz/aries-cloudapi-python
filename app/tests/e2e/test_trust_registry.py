import pytest

from assertpy import assert_that
from fastapi import HTTPException

from app.models.definitions import CredentialSchema
from app.models.tenants import CreateTenantResponse
from app.routes.trust_registry import router

from shared.constants import CLOUDAPI_URL
from shared.util.rich_async_client import RichAsyncClient

TRUST_REGISTRY = router.prefix


@pytest.mark.anyio
async def test_get_schemas(
    schema_definition: CredentialSchema, schema_definition_alt: CredentialSchema
):
    async with RichAsyncClient() as client:
        schemas_response = await client.get(f"{CLOUDAPI_URL}{TRUST_REGISTRY}/schemas")

    assert schemas_response.status_code == 200
    schemas = schemas_response.json()
    assert len(schemas) >= 2


@pytest.mark.anyio
async def test_get_schema_by_id(schema_definition: CredentialSchema):
    async with RichAsyncClient() as client:
        schema_response = await client.get(
            f"{CLOUDAPI_URL}{TRUST_REGISTRY}/schemas/{schema_definition.id}"
        )

    assert schema_response.status_code == 200
    schema = schema_response.json()
    assert_that(schema).contains("did", "name", "version", "id")

    with pytest.raises(HTTPException) as exc:
        async with RichAsyncClient() as client:
            schema_response = await client.get(
                f"{CLOUDAPI_URL}{TRUST_REGISTRY}/schemas/bad_schema_id"
            )

    assert exc.value.status_code == 404
