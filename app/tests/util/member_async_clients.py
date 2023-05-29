import pytest

from app.admin.tenants.models import CreateTenantResponse
from app.tests.util.client import (
    get_governance_client,
    get_tenant_admin_client,
    get_tenant_client,
)
from app.tests.util.tenants import create_issuer_tenant, delete_tenant


@pytest.fixture(scope="function")
async def governance_client():
    async with get_governance_client() as async_client:
        yield async_client


@pytest.fixture(scope="function")
async def tenant_admin_client():
    async with get_tenant_admin_client() as async_client:
        yield async_client


@pytest.fixture(scope="function")
async def alice_member_client(alice_tenant: CreateTenantResponse):
    alice_client = get_tenant_client(token=alice_tenant.access_token)

    yield alice_client

    await alice_client.aclose()


@pytest.fixture(scope="function")
async def bob_member_client():
    async with get_tenant_admin_client() as admin_async_client:
        tenant = await create_issuer_tenant(admin_async_client, "bob")

        bob_client = get_tenant_client(token=tenant.access_token)
        yield bob_client

        await bob_client.aclose()

        await delete_tenant(admin_async_client, tenant.tenant_id)


@pytest.fixture(scope="function")
async def faber_client():
    async with get_tenant_admin_client() as admin_async_client:
        faber_issuer = await create_issuer_tenant(admin_async_client, "faber")

        faber_async_client = get_tenant_client(token=faber_issuer.access_token)
        yield faber_async_client

        await faber_async_client.aclose()

        await delete_tenant(admin_async_client, faber_issuer.tenant_id)


@pytest.fixture(scope="function")
async def acme_client(acme_tenant: CreateTenantResponse):
    acme_async_client = get_tenant_client(token=acme_tenant.access_token)
    yield acme_async_client

    await acme_async_client.aclose()
