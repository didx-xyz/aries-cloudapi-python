import pytest

from app.tests.util.client import get_tenant_admin_client
from app.tests.util.tenants import (
    create_issuer_tenant,
    create_tenant,
    create_verifier_tenant,
    delete_tenant,
)


@pytest.fixture(scope="session")
async def alice_tenant():
    async with get_tenant_admin_client() as admin_client:
        tenant = await create_tenant(admin_client, "alice")

        yield tenant

        await delete_tenant(admin_client, tenant.tenant_id)


@pytest.fixture(scope="session")
async def bob_tenant():
    async with get_tenant_admin_client() as admin_client:
        tenant = await create_issuer_tenant(admin_client, "bob")

        yield tenant

        await delete_tenant(admin_client, tenant.tenant_id)


@pytest.fixture(scope="session")
async def acme_verifier():
    async with get_tenant_admin_client() as admin_client:
        verifier_tenant = await create_verifier_tenant(admin_client, "acme")

        yield verifier_tenant

        await delete_tenant(admin_client, verifier_tenant.tenant_id)


@pytest.fixture(scope="session")
async def faber_issuer():
    async with get_tenant_admin_client() as admin_client:
        issuer_tenant = await create_issuer_tenant(admin_client, "faber")

        yield issuer_tenant

        await delete_tenant(admin_client, issuer_tenant.tenant_id)
