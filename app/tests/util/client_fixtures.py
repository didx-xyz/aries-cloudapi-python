import pytest

from app.tests.util.client import (
    get_governance_acapy_client,
    get_governance_client,
    get_tenant_admin_acapy_client,
    get_tenant_admin_client,
)


# Governance
@pytest.fixture(scope="session")
async def governance_acapy_client():
    acapy_client = get_governance_acapy_client()
    yield acapy_client()

    await acapy_client.close()


@pytest.fixture(scope="function")
async def governance_client():
    async with get_governance_client() as async_client:
        yield async_client


# Tenant Admin
@pytest.fixture(scope="function")
async def tenant_admin_client():
    async with get_tenant_admin_client() as async_client:
        yield async_client


@pytest.fixture(scope="function")
async def tenant_admin_acapy_client():
    acapy_client = get_tenant_admin_acapy_client()
    yield acapy_client

    await acapy_client.close()
