import pytest
from aries_cloudcontroller import AriesAgentControllerBase
from aries_cloudcontroller.controllers.ledger import LedgerController
from aries_cloudcontroller.controllers.wallet import WalletController
from httpx import AsyncClient
from mockito import mock

import ledger_facade
import utils
from main import app


@pytest.fixture
def setup_env():
    utils.admin_url = "http://localhost"
    utils.admin_port = "3021"
    utils.is_multitenant = False
    ledger_facade.LEDGER_URL = "http://testnet.didx.xyz/register"
    ledger_facade.LEDGER_TYPE = "von"


@pytest.fixture
def mock_agent_controller():
    controller = mock(AriesAgentControllerBase)
    controller.wallet = mock(WalletController)
    controller.ledger = mock(LedgerController)
    return controller


@pytest.fixture
async def async_client():
    async with AsyncClient(app=app, base_url="http://localhost:8000") as ac:
        yield ac
