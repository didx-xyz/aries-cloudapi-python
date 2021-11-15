import json
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Dict, TypedDict
import os

import pytest
from aries_cloudcontroller import (
    AcaPyClient,
    CredentialsApi,
    IssueCredentialV10Api,
    IssueCredentialV20Api,
    LedgerApi,
    WalletApi,
)
from assertpy import assert_that
from httpx import AsyncClient
from mockito import mock

from app.generic.connections.connections import CONNECTIONS_ROUTE as BASE_PATH_CON
import app.facades.ledger as ledger_facade
import app.utils as utils
from app.dependencies import member_admin_agent, yoma_agent
from app.main import app

from .test_dependencies import async_next
from .utils_test import get_random_string

DEFAULT_HEADERS = {
    "content-type": "application/json",
    "x-role": "member",
    "x-api-key": "adminApiKey",
}

LEDGER_URL = os.getenv("TEST_LEDGER_URL", "http://localhost:9000/register")
X_API_KEY = os.getenv("X_API_KEY", "adminApiKey")
CONFTEST_ADMIN_URL = os.getenv("CONFTEST_ADMIN_URL", "http://localhost")
CONFTEST_ADMIN_PORT = os.getenv("CONFTEST_ADMIN_PORT", "3021")
CONFTEST_IS_MULTITENANT = bool(os.getenv("CONFTEST_IS_MULTITENANT", "False"))
CONFTEST_LEDGER_TYPE = os.getenv("CONFTEST_LEDGER_TYPE", "von")


class AliceBobConnect(TypedDict):
    alice_connection_id: str
    bob_connection_id: str


@pytest.fixture
def setup_env():
    utils.admin_url = CONFTEST_ADMIN_URL
    utils.admin_port = CONFTEST_ADMIN_PORT
    utils.is_multitenant = CONFTEST_IS_MULTITENANT
    ledger_facade.LEDGER_URL = LEDGER_URL
    ledger_facade.LEDGER_TYPE = CONFTEST_LEDGER_TYPE


@pytest.fixture
def mock_agent_controller():
    controller = mock(AcaPyClient)
    controller.wallet = mock(WalletApi)
    controller.ledger = mock(LedgerApi)
    controller.issue_credential_v1_0 = mock(IssueCredentialV10Api)
    controller.issue_credential_v2_0 = mock(IssueCredentialV20Api)
    controller.credentials = mock(CredentialsApi)
    return controller


@pytest.fixture(scope="module")
async def yoma_agent_module_scope():
    # fast api auto wraps the generator functions use for dependencies as context managers - thus why the
    # async context manager decorator is not required.
    # it is a bit of a pity that pytest fixtures don't do the same - I guess they want to maintain
    # flexibility - thus we have to.
    # this is doing what using decorators does for you
    async with asynccontextmanager(yoma_agent)(x_api_key=X_API_KEY) as c:
        yield c


@pytest.fixture
async def yoma_agent_mock():
    # fast api auto wraps the generator functions use for dependencies as context managers - thus why the
    # async context manager decorator is not required.
    # it is a bit of a pity that pytest fixtures don't do the same - I guess they want to maintain
    # flexibility - thus we have to.
    # this is doing what using decorators does for you
    async with asynccontextmanager(yoma_agent)(x_api_key=X_API_KEY) as c:
        yield c


@pytest.fixture
async def async_client():
    async with AsyncClient(app=app, base_url="http://localhost:8000") as ac:
        yield ac


@pytest.fixture
async def member_admin_agent_mock():
    async with asynccontextmanager(member_admin_agent)(x_api_key=X_API_KEY) as c:
        yield c


@dataclass
class AgentEntity:
    headers: Dict[str, str]
    did: str
    pub_did: str
    verkey: str
    token: str


@pytest.fixture()
async def async_client_bob(async_client):
    async with agent_client(async_client, "bob") as client:
        yield client


@pytest.fixture(scope="module")
async def async_client_bob_module_scope():
    async with AsyncClient(app=app, base_url="http://localhost:8000") as async_client:
        async with agent_client(async_client, "bob") as client:
            yield client


@pytest.fixture()
async def async_client_alice(async_client):
    async with agent_client(async_client, "alice") as client:
        yield client


@pytest.fixture(scope="module")
async def async_client_alice_module_scope():
    async with AsyncClient(app=app, base_url="http://localhost:8000") as async_client:
        async with agent_client(async_client, "alice") as client:
            yield client


@asynccontextmanager
async def agent_client(async_client, name):
    agent = await async_next(create_wallet(async_client, name))
    async with AsyncClient(
        app=app, base_url="http://localhost:8000", headers=agent.headers
    ) as ac:
        ac.agent = agent
        yield ac


@pytest.fixture
async def member_bob(async_client):
    return await async_next(create_wallet(async_client, "bob"))


@pytest.fixture
async def member_alice(async_client):
    return await async_next(create_wallet(async_client, "alice"))


async def create_wallet(async_client, key):
    def create_wallet_payload(key):
        return {
            "image_url": "https://aries.ca/images/sample.png",
            "label": f"{key}{get_random_string(3)}",
            "wallet_key": "MySecretKey1234",
            "wallet_name": f"{key}{get_random_string(3)}",
        }

    wallet_payload = create_wallet_payload(key)

    wallet = (
        await async_client.post(
            "/admin/wallet-multitenant" + "/create-wallet",
            headers=DEFAULT_HEADERS,
            data=json.dumps(wallet_payload),
        )
    ).json()

    local_did = (
        await async_client.get(
            "/wallet/create-local-did",
            headers={**DEFAULT_HEADERS, "x-auth": f"Bearer {wallet['token']}"},
        )
    ).json()
    public_did = (
        await async_client.get(
            "/wallet/create-pub-did",
            headers={**DEFAULT_HEADERS, "x-auth": f"Bearer {wallet['token']}"},
        )
    ).json()
    yield AgentEntity(
        headers={**DEFAULT_HEADERS, "x-auth": f'Bearer {wallet["token"]}'},
        did=local_did["result"]["did"],
        pub_did=public_did["did_object"]["did"],
        verkey=local_did["result"]["verkey"],
        token=wallet["token"],
    )
    connections = (await async_client.get("/generic/connections")).json()
    for c in connections["result"]:
        await async_client.delete(f"/generic/connections/{c['connection_id']}")

    await async_client.delete(
        f"/admin/wallet-multitenant/{wallet['wallet_id']}",
        headers=DEFAULT_HEADERS,
    )


@pytest.fixture(scope="module")
@pytest.mark.asyncio
async def create_bob_and_alice_connect(
    async_client_bob_module_scope: AsyncClient,
    async_client_alice_module_scope: AsyncClient,
) -> AliceBobConnect:
    """This test validates that bob and alice connect successfully."""

    async_client_bob = async_client_bob_module_scope
    async_client_alice = async_client_alice_module_scope
    # create invitation on bob side
    invitation = (
        await async_client_bob.post(BASE_PATH_CON + "/create-invitation")
    ).json()
    bob_conn_id = invitation["connection_id"]
    connections = (await async_client_bob.get(BASE_PATH_CON)).json()
    assert_that(connections).extracting("connection_id").contains_only(bob_conn_id)

    # accept invitation on alice side
    invitation_response = (
        await async_client_alice.post(
            BASE_PATH_CON + "/accept-invitation",
            json={"invitation": invitation["invitation"]},
        )
    ).json()
    time.sleep(15)
    alice_conn_id = invitation_response["connection_id"]
    # fetch and validate
    # both connections should be active - we have waited long enough for events to be exchanged
    # and we are running in "auto connect" mode.
    bob_connections = (await async_client_bob.get(BASE_PATH_CON)).json()
    alice_connections = (await async_client_alice.get(BASE_PATH_CON)).json()

    assert_that(bob_connections).extracting("connection_id").contains(bob_conn_id)
    bob_connection = [c for c in bob_connections if c["connection_id"] == bob_conn_id][
        0
    ]
    assert_that(bob_connection).has_state("completed")

    assert_that(alice_connections).extracting("connection_id").contains(alice_conn_id)
    alice_connection = [
        c for c in alice_connections if c["connection_id"] == alice_conn_id
    ][0]
    assert_that(alice_connection).has_state("completed")

    return {
        "alice_connection_id": alice_conn_id,
        "bob_connection_id": bob_conn_id,
    }


@pytest.fixture(scope="module")
def bob_connection_id(create_bob_and_alice_connect: AliceBobConnect):
    return create_bob_and_alice_connect["bob_connection_id"]


@pytest.fixture(scope="module")
def alice_connection_id(create_bob_and_alice_connect: AliceBobConnect):
    return create_bob_and_alice_connect["alice_connection_id"]
