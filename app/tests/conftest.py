import pytest

import ledger_facade
import utils


@pytest.fixture
def setup_env():
    utils.admin_url = "http://localhost"
    utils.admin_port = "3021"
    utils.is_multitenant = False
    ledger_facade.LEDGER_URL = "http://testnet.didx.xyz/register"
    ledger_facade.LEDGER_TYPE = 'von'
