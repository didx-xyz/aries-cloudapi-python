import pytest
from aries_cloudcontroller.model import TAAAccept, TAARecord, TAAResult
from aries_cloudcontroller.model.taa_info import TAAInfo
from fastapi import HTTPException
from mockito import when

from app.acapy_ledger_facade import accept_taa, get_did_endpoint, get_taa


# need this to handle the async with the mock
async def get(response):
    return response


@pytest.mark.asyncio
async def test_error_on_get_taa(mock_agent_controller):
    when(mock_agent_controller.ledger).fetch_taa().thenReturn(
        get(TAAResult(result=TAAInfo(taa_required=True)))
    )

    with pytest.raises(HTTPException) as exc:
        await get_taa(mock_agent_controller)
    assert exc.value.status_code == 404
    assert "Something went wrong. Could not get TAA." in exc.value.detail


@pytest.mark.asyncio
async def test_error_on_accept_taa(mock_agent_controller):
    error_response = {"x": "y"}
    when(mock_agent_controller.ledger).accept_taa(
        body=TAAAccept(mechanism="data", text=None, version=None)
    ).thenReturn(get(error_response))

    record = TAARecord(digest="")
    with pytest.raises(HTTPException) as exc:
        await accept_taa(mock_agent_controller, taa=record, mechanism="data")
    assert exc.value.status_code == 404
    assert (
        exc.value.detail
        == f"Something went wrong. Could not accept TAA. {str(error_response)}"
    )


@pytest.mark.asyncio
async def test_error_on_get_did_endpoint(mock_agent_controller):
    when(mock_agent_controller.ledger).get_did_endpoint(did="data").thenReturn(
        get(None)
    )

    with pytest.raises(HTTPException) as exc:
        await get_did_endpoint(mock_agent_controller, "data")
    assert exc.value.status_code == 404
    assert exc.value.detail == "Something went wrong. Could not obtain issuer endpoint."
