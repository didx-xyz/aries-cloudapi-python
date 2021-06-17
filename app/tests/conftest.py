import pytest

import facade
import ledger_facade


@pytest.fixture
def setup_env():
    facade.admin_url = "http://localhost"
    facade.admin_port = "3021"
    facade.is_multitenant = False
    ledger_facade.ledger_url = "https://selfserve.sovrin.org/nym"
