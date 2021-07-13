import pytest
from acapy_ledger_facade import accept_taa, get_did_endpoint, get_taa
from fastapi import HTTPException
from mockito import when


# need this to handle the async with the mock
async def get(response):
    return response


@pytest.mark.asyncio
async def test_error_on_get_taa(mock_agent_controller):
    when(mock_agent_controller.ledger).get_taa().thenReturn(get({}))

    with pytest.raises(HTTPException) as exc:
        await get_taa(mock_agent_controller)
    assert exc.value.status_code == 404
    assert exc.value.detail == "Something went wrong. Could not get TAA. {}"


@pytest.mark.asyncio
async def test_error_on_accept_taa(mock_agent_controller):
    error_response = {"x": "y"}
    when(mock_agent_controller.ledger).accept_taa("data").thenReturn(
        get(error_response)
    )

    with pytest.raises(HTTPException) as exc:
        await accept_taa(mock_agent_controller, "data")
    assert exc.value.status_code == 404
    assert (
        exc.value.detail
        == f"Something went wrong. Could not accept TAA. {str(error_response)}"
    )


@pytest.mark.asyncio
async def test_error_on_get_did_endpoint(mock_agent_controller):
    when(mock_agent_controller.ledger).get_did_endpoint("data").thenReturn(get(None))

    with pytest.raises(HTTPException) as exc:
        await get_did_endpoint(mock_agent_controller, "data")
    assert exc.value.status_code == 404
    assert (
        exc.value.detail == f"Something went wrong. Could not obtain issuer endpoint."
    )
