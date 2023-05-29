import pytest

from app.tests.util.client import (
    get_governance_acapy_client,
    get_tenant_acapy_client,
    get_tenant_admin_acapy_client,
)
from app.util.rich_async_client import RichAsyncClient


@pytest.fixture(scope="module")
async def governance_acapy_client():
    acapy_client = get_governance_acapy_client()
    yield acapy_client

    await acapy_client.close()


@pytest.fixture(scope="function")
async def tenant_admin_acapy_client():
    acapy_client = get_tenant_admin_acapy_client()
    yield acapy_client

    await acapy_client.close()


@pytest.fixture(scope="function")
async def alice_acapy_client(alice_member_client: RichAsyncClient):
    [_, token] = alice_member_client.headers.get("x-api-key").split(".", maxsplit=1)

    client = get_tenant_acapy_client(token=token)
    yield client

    await client.close()


@pytest.fixture(scope="function")
async def bob_acapy_client(bob_member_client: RichAsyncClient):
    # We extract the token from the x-api-key header as that's the easiest
    # method to create an AcaPyClient from an AsyncClient
    [_, token] = bob_member_client.headers.get("x-api-key").split(".", maxsplit=1)

    client = get_tenant_acapy_client(token=token)
    yield client

    await client.close()


@pytest.fixture(scope="function")
async def faber_acapy_client(faber_client: RichAsyncClient):
    # We extract the token from the x-api-key header as that's the easiest
    # method to create an AcaPyClient from an AsyncClient
    [_, token] = faber_client.headers.get("x-api-key").split(".", maxsplit=1)

    client = get_tenant_acapy_client(token=token)
    yield client

    await client.close()


@pytest.fixture(scope="function")
async def acme_acapy_client(faber_client: RichAsyncClient):
    # We extract the token from the x-api-key header as that's the easiest
    # method to create an AcaPyClient from an AsyncClient
    [_, token] = faber_client.headers.get("x-api-key").split(".", maxsplit=1)

    client = get_tenant_acapy_client(token=token)
    yield client

    await client.close()
