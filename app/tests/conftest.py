import json
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Dict

import ledger_facade
import pytest
import utils
from aries_cloudcontroller import AriesAgentControllerBase
from aries_cloudcontroller.controllers.ledger import LedgerController
from aries_cloudcontroller.controllers.wallet import WalletController
from dependencies import member_admin_agent, yoma_agent
from httpx import AsyncClient
from main import app
from mockito import mock

from tests.test_dependencies import async_next
from tests.utils_test import get_random_string

DEFAULT_HEADERS = {
    "content-type": "application/json",
    "x-role": "member",
    "x-api-key": "adminApiKey",
}


@pytest.fixture
def setup_env():
    utils.admin_url = "http://localhost"
    utils.admin_port = "3021"
    utils.is_multitenant = False
    ledger_facade.LEDGER_URL = "http://localhost:9000/register"
    ledger_facade.LEDGER_TYPE = "von"


@pytest.fixture
def mock_agent_controller():
    controller = mock(AriesAgentControllerBase)
    controller.wallet = mock(WalletController)
    controller.ledger = mock(LedgerController)
    return controller


@pytest.fixture(scope="module")
async def yoma_agent_module_scope():
    # fast api auto wraps the generator functions use for dependencies as context managers - thus why the
    # async context manager decorator is not required.
    # it is a bit of a pity that pytest fixtures don't do the same - I guess they want to maintain
    # flexibility - thus we have to.
    # this is doing what using decorators does for you
    async with asynccontextmanager(yoma_agent)(x_api_key="adminApiKey") as c:
        yield c


@pytest.fixture
async def yoma_agent_mock():
    # fast api auto wraps the generator functions use for dependencies as context managers - thus why the
    # async context manager decorator is not required.
    # it is a bit of a pity that pytest fixtures don't do the same - I guess they want to maintain
    # flexibility - thus we have to.
    # this is doing what using decorators does for you
    async with asynccontextmanager(yoma_agent)(x_api_key="adminApiKey") as c:
        yield c


@pytest.fixture
async def async_client():
    async with AsyncClient(app=app, base_url="http://localhost:8000") as ac:
        yield ac


@pytest.fixture
async def member_admin_agent_mock():
    async with asynccontextmanager(member_admin_agent)(x_api_key="adminApiKey") as c:
        yield c


@dataclass
class AgentEntity:
    headers: Dict[str, str]
    wallet_id: str
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
            headers={**DEFAULT_HEADERS, "authorization": f"Bearer {wallet['token']}"},
        )
    ).json()
    public_did = (
        await async_client.get(
            "/wallet/create-pub-did",
            headers={**DEFAULT_HEADERS, "authorization": f"Bearer {wallet['token']}"},
        )
    ).json()

    yield AgentEntity(
        headers={**DEFAULT_HEADERS, "authorization": f'Bearer {wallet["token"]}'},
        wallet_id=wallet["wallet_id"],
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
