import facade
import ledger_facade
import pytest
from core import wallet
from fastapi import HTTPException


@pytest.fixture
def setup_env():
    facade.admin_url = "http://localhost"
    facade.admin_port = "3021"
    facade.is_multitenant = False
    ledger_facade.ledger_url = "https://selfserve.sovrin.org/nym"


@pytest.mark.asyncio
async def test_create_public_did(setup_env):
    result = await wallet.create_public_did("{'api_key':'adminApiKey'}")

    # TODO: validate in a more robust manner
    assert result.did_object and result.did_object != {}
    assert result.issuer_verkey and result.issuer_verkey != {}
    assert result.issuer_endpoint and result.issuer_endpoint != {}


@pytest.mark.asyncio
async def test_create_public_did_no_api_key(setup_env):

    with pytest.raises(HTTPException) as exc:
        await wallet.create_public_did("")
    assert exc.value.status_code == 400
    assert (
        exc.value.detail
        == "Bad headers. Either provide an api_key or both wallet_id and tenant_jwt"
    )
