import pytest

from app.tests.util.client import get_tenant_admin_client
from app.tests.util.tenants import create_tenant, create_verifier_tenant, delete_tenant


@pytest.fixture(scope="function")
async def alice_tenant():
    async with get_tenant_admin_client() as client:
        tenant = await create_tenant(client, "alice")

        yield tenant

        await delete_tenant(client, tenant.tenant_id)


@pytest.fixture(scope="function")
async def acme_tenant():
    async with get_tenant_admin_client() as client:
        tenant = await create_verifier_tenant(client, "acme")

        yield tenant

        await delete_tenant(client, tenant.tenant_id)
