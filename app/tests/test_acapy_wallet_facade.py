import pytest
from acapy_wallet_facade import assign_pub_did, create_did, get_pub_did
from aries_cloudcontroller import AcaPyClient
from aries_cloudcontroller.api.wallet import WalletApi
from fastapi import HTTPException
from mockito import mock, when


# need this to handle the async with the mock
async def get():
    return {}


@pytest.fixture
def mock_agent_controller():
    controller = mock(AcaPyClient)
    controller.wallet = mock(WalletController)
    return controller


@pytest.mark.asyncio
async def test_error_on_get_pub_did(mock_agent_controller):
    when(mock_agent_controller.wallet).get_public_did().thenReturn(get())

    with pytest.raises(HTTPException) as exc:
        await get_pub_did(mock_agent_controller)
    assert exc.value.status_code == 404
    assert exc.value.detail == "Something went wrong. Could not obtain public DID. {}"


@pytest.mark.asyncio
async def test_error_on_assign_pub_did(mock_agent_controller):
    when(mock_agent_controller.wallet).assign_public_did("did").thenReturn(get())

    with pytest.raises(HTTPException) as exc:
        await assign_pub_did(mock_agent_controller, "did")
    assert exc.value.status_code == 500
    assert exc.value.detail == "Something went wrong.\nCould not assign DID. {}"


@pytest.mark.asyncio
async def test_error_on_create_pub_did(mock_agent_controller):
    when(mock_agent_controller.wallet).create_did().thenReturn(get())

    with pytest.raises(HTTPException) as exc:
        await create_did(mock_agent_controller)
    assert exc.value.status_code == 404
    assert exc.value.detail == "Something went wrong.\nCould not generate DID.\n{}"
