import pytest

import routers.governance
from core import wallet, agent_factory, delegates


def test_foo():
    pass


@pytest.mark.asyncio
async def test_create_public_did():
    agent_factory.admin_url = 'http://0.0.0.0'
    agent_factory.admin_port = '3021'
    agent_factory.admin_api_key = 'adminApiKey'
    agent_factory.is_multitenant = False

    delegates.ledger_url = "https://selfserve.sovrin.org/nym"
    result = await wallet.create_public_did()
    print(result)
