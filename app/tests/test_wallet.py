
import pytest
from assertpy import assert_that

from core import wallet, agent_factory, delegates


def test_foo():
    pass


@pytest.mark.asyncio
async def test_create_public_did():
    setup_env()

    result = await wallet.create_public_did()

    # TODO: validate in a more robust manner
    assert_that(result.did_object).is_not_empty()
    assert_that(result.issuer_verkey).is_not_empty()
    assert_that(result.issuer_endpoint).is_not_empty()


def setup_env():
    agent_factory.admin_url = 'http://localhost'
    agent_factory.admin_port = '3021'
    agent_factory.admin_api_key = 'adminApiKey'
    agent_factory.is_multitenant = False
    delegates.ledger_url = "https://selfserve.sovrin.org/nym"
