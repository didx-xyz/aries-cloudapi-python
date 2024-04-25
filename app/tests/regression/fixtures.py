import pytest
from typing import Any, AsyncGenerator

from app.models.tenants import CreateTenantRequest, CreateTenantResponse
from app.tests.util.client import get_tenant_admin_client
from app.tests.util.tenants import (
    TENANT_BASE_PATH,
    post_tenant_request,
)
from shared.util.rich_async_client import RichAsyncClient

regression_tests_group_id = "RegressionTests"


async def get_or_create_tenant(
    admin_client: RichAsyncClient, name: str, roles: list[str] = []
) -> CreateTenantResponse:
    # Fetch all tenants in the regression test group
    list_tenants = await admin_client.get(
        TENANT_BASE_PATH, params={"group_id": regression_tests_group_id}
    ).json()

    # Try to find the tenant by the specific role or name
    for tenant in list_tenants:
        if tenant["wallet_label"] == name:
            return tenant  # Return existing tenant if found

    # If not found, create a new tenant
    request = CreateTenantRequest(
        wallet_label=name,
        group_id=regression_tests_group_id,
        roles=roles,
    )
    return await post_tenant_request(admin_client, request)


@pytest.fixture(scope="session")
async def holder_tenant() -> AsyncGenerator[CreateTenantResponse, Any]:
    async with get_tenant_admin_client() as admin_client:
        tenant = await get_or_create_tenant(
            admin_client, "RegressionTestHolder", roles=[]
        )
        yield tenant


@pytest.fixture(scope="session")
async def issuer_tenant() -> AsyncGenerator[CreateTenantResponse, Any]:
    async with get_tenant_admin_client() as admin_client:
        tenant = await get_or_create_tenant(
            admin_client, "RegressionTestIssuer", roles=["issuer"]
        )
        yield tenant


@pytest.fixture(scope="session")
async def verifier_tenant() -> AsyncGenerator[CreateTenantResponse, Any]:
    async with get_tenant_admin_client() as admin_client:
        tenant = await get_or_create_tenant(
            admin_client, "RegressionTestVerifier", roles=["verifier"]
        )
        yield tenant
