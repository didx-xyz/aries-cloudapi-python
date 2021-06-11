
import pytest
from assertpy import assert_that

import facade
import ledger_facade
from core import wallet


def test_foo():
    pass


@pytest.mark.asyncio
async def test_create_public_did():
    setup_env()

    result = await wallet.create_public_did("")

    # TODO: validate in a more robust manner
    assert_that(result.did_object).is_not_empty()
    assert_that(result.issuer_verkey).is_not_empty()
    assert_that(result.issuer_endpoint).is_not_empty()


def setup_env():
    facade.admin_url = 'http://localhost'
    facade.admin_port = '3021'
    facade.admin_api_key = 'adminApiKey'
    facade.is_multitenant = False
    ledger_facade.ledger_url = "https://selfserve.sovrin.org/nym"
