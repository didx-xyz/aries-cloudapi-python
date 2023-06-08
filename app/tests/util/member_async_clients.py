from typing import Any, Generator

import pytest

from app.admin.tenants.models import CreateTenantResponse
from app.tests.util.client import (
    get_governance_client,
    get_tenant_admin_client,
    get_tenant_client,
)
from shared import RichAsyncClient


@pytest.fixture(scope="session")
async def governance_client() -> Generator[RichAsyncClient, Any, None]:
    async with get_governance_client() as gov_async_client:
        yield gov_async_client


@pytest.fixture(scope="function")
async def tenant_admin_client() -> Generator[RichAsyncClient, Any, None]:
    async with get_tenant_admin_client() as admin_async_client:
        yield admin_async_client


@pytest.fixture(scope="function")
async def alice_member_client(
    alice_tenant: CreateTenantResponse,
) -> Generator[RichAsyncClient, Any, None]:
    async with get_tenant_client(token=alice_tenant.access_token) as alice_async_client:
        yield alice_async_client


@pytest.fixture(scope="function")
async def bob_member_client(
    bob_tenant: CreateTenantResponse,
) -> Generator[RichAsyncClient, Any, None]:
    async with get_tenant_client(token=bob_tenant.access_token) as bob_async_client:
        yield bob_async_client


@pytest.fixture(scope="function")
async def faber_client(
    faber_issuer: CreateTenantResponse,
) -> Generator[RichAsyncClient, Any, None]:
    async with get_tenant_client(token=faber_issuer.access_token) as faber_async_client:
        yield faber_async_client


@pytest.fixture(scope="function")
async def acme_client(
    acme_verifier: CreateTenantResponse,
) -> Generator[RichAsyncClient, Any, None]:
    async with get_tenant_client(token=acme_verifier.access_token) as acme_async_client:
        yield acme_async_client
