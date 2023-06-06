import pytest

from app.tests.util.client import (
    get_governance_acapy_client,
    get_tenant_acapy_client,
    get_tenant_admin_acapy_client,
)
from shared import RichAsyncClient


@pytest.fixture(scope="session")
async def governance_acapy_client():
    acapy_client = get_governance_acapy_client()
    yield acapy_client

    await acapy_client.close()


@pytest.fixture(scope="session")
async def tenant_admin_acapy_client():
    acapy_client = get_tenant_admin_acapy_client()
    yield acapy_client

    await acapy_client.close()


def get_token(client):
    # We extract the token from the x-api-key header as that's the easiest
    # method to create an AcaPyClient from an AsyncClient
    [_, token] = client.headers.get("x-api-key").split(".", maxsplit=1)
    return token


@pytest.fixture(scope="session")
async def alice_acapy_client(alice_member_client: RichAsyncClient):
    acapy_client = get_tenant_acapy_client(token=get_token(alice_member_client))
    yield acapy_client

    await acapy_client.close()


@pytest.fixture(scope="session")
async def bob_acapy_client(bob_member_client: RichAsyncClient):
    acapy_client = get_tenant_acapy_client(token=get_token(bob_member_client))
    yield acapy_client

    await acapy_client.close()


@pytest.fixture(scope="session")
async def faber_acapy_client(faber_client: RichAsyncClient):
    acapy_client = get_tenant_acapy_client(token=get_token(faber_client))
    yield acapy_client

    await acapy_client.close()


@pytest.fixture(scope="session")
async def acme_acapy_client(acme_client: RichAsyncClient):
    acapy_client = get_tenant_acapy_client(token=get_token(acme_client))
    yield acapy_client

    await acapy_client.close()
