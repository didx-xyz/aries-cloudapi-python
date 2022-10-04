import pytest
from aries_cloudcontroller import (
    AcaPyClient,
    TAAAccept,
    TAAInfo,
    TAARecord,
    TAAResult,
    SchemaGetResult,
    ModelSchema,
)
from fastapi import HTTPException
from mockito import verify, when
from assertpy import assert_that

from app.facades.acapy_ledger import (
    accept_taa,
    get_did_endpoint,
    get_taa,
    schema_id_from_credential_definition_id,
)
from app.tests.util.event_loop import get


@pytest.mark.asyncio
async def test_error_on_get_taa(mock_agent_controller: AcaPyClient):
    when(mock_agent_controller.ledger).fetch_taa().thenReturn(
        get(TAAResult(result=TAAInfo(taa_required=True)))
    )

    with pytest.raises(HTTPException) as exc:
        await get_taa(mock_agent_controller)
    assert exc.value.status_code == 404
    assert "Something went wrong. Could not get TAA." in exc.value.detail


@pytest.mark.asyncio
async def test_error_on_accept_taa(mock_agent_controller: AcaPyClient):
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
async def test_error_on_get_did_endpoint(mock_agent_controller: AcaPyClient):
    when(mock_agent_controller.ledger).get_did_endpoint(did="data").thenReturn(
        get(None)
    )

    with pytest.raises(HTTPException) as exc:
        await get_did_endpoint(mock_agent_controller, "data")
    assert exc.value.status_code == 404
    assert exc.value.detail == "Something went wrong. Could not obtain issuer endpoint."


@pytest.mark.asyncio
async def test_schema_id_from_credential_definition_id_seq_no(
    mock_agent_controller: AcaPyClient,
):
    schema_id = "Ehx3RZSV38pn3MYvxtHhbQ:2:schema_name:1.0.1"
    seq_no = "58278"
    cred_def_id_seq_no = "Ehx3RZSV38pn3MYvxtHhbQ:3:CL:58278:tag"

    when(mock_agent_controller.schema).get_schema(schema_id=seq_no).thenReturn(
        get(
            SchemaGetResult(
                schema_=ModelSchema(
                    id=schema_id,
                )
            )
        )
    )

    schema_id = await schema_id_from_credential_definition_id(
        mock_agent_controller, cred_def_id_seq_no
    )

    assert_that(schema_id).is_equal_to(schema_id)
    verify(mock_agent_controller.schema).get_schema(schema_id=seq_no)


@pytest.mark.asyncio
async def test_schema_id_from_credential_definition_id_schema_id(
    mock_agent_controller: AcaPyClient,
):
    schema_id = "Ehx3RZSV38pn3MYvxtHhbQ:2:schema_name:1.0.1"
    cred_def_id_schema_id = f"Ehx3RZSV38pn3MYvxtHhbQ:3:CL:{schema_id}:tag"

    when(mock_agent_controller.schema).get_schema(...)

    schema_id = await schema_id_from_credential_definition_id(
        mock_agent_controller, cred_def_id_schema_id
    )

    verify(mock_agent_controller.schema, times=0).get_schema(...)
    assert_that(schema_id).is_equal_to(schema_id)
