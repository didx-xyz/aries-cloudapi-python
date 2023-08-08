import pytest
from aries_cloudcontroller import (
    AcaPyClient,
    CredAttrSpec,
    CredentialPreview,
    CredentialProposal,
    V10CredentialExchange,
    V10CredentialExchangeListResult,
    V10CredentialStoreRequest,
)
from assertpy import assert_that
from mockito import when

from app.models.issuer import CredentialWithConnection
from app.services.issuer.acapy_issuer_v1 import IssuerV1
from app.tests.util.mock import to_async

v1_credential_exchange_records = [
    V10CredentialExchange(
        credential_definition_id="WgWxqztrNooG92RXvxSTWv:3:CL:20:tag1",
        created_at="2021-09-15 14:41:47Z",
        role="issuer",
        updated_at="2021-09-15 14:49:47Z",
        schema_id="WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0",
        state="offer_sent",
        connection_id="3fa85f64-5717-4562-b3fc-2c963f66afb9",
        credential_proposal_dict=CredentialProposal(
            credential_proposal=CredentialPreview(
                attributes=[CredAttrSpec(name="speed", value="10")]
            )
        ),
        credential_exchange_id="db9d7025-b276-4c32-ae38-fbad41864112",
    ),
    V10CredentialExchange(
        credential_definition_id="WgWxqztrNooG92RXvxSTWv:3:CL:20:tag2",
        created_at="2021-09-15 13:49:47Z",
        role="holder",
        updated_at="2021-09-15 13:51:47Z",
        schema_id="WgWxqztrNooG92RXvxSTWv:2:schema_name:1.1",
        state="offer_sent",
        connection_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
        credential_proposal_dict=CredentialProposal(
            credential_proposal=CredentialPreview(
                attributes=[CredAttrSpec(name="speed", value="10")]
            )
        ),
        credential_exchange_id="dabc8f4e-164a-410f-bd10-471b090f65a5",
        credential_id="16c83f10-c205-4305-aa6f-cefa2d7da160",
    ),
]


@pytest.mark.anyio
async def test_get_records(mock_agent_controller: AcaPyClient):
    when(mock_agent_controller.issue_credential_v1_0).get_records(...).thenReturn(
        to_async(
            V10CredentialExchangeListResult(results=v1_credential_exchange_records)
        )
    )

    records = await IssuerV1.get_records(mock_agent_controller)

    assert len(records) == len(v1_credential_exchange_records)
    assert_that(map(lambda c: c.credential_id, records)).contains(
        f"v1-{v1_credential_exchange_records[0].credential_exchange_id}",
        f"v1-{v1_credential_exchange_records[1].credential_exchange_id}",
    )


@pytest.mark.anyio
async def test_get_records_connection_id(mock_agent_controller: AcaPyClient):
    record = v1_credential_exchange_records[0]

    when(mock_agent_controller.issue_credential_v1_0).get_records(
        connection_id=record.connection_id
    ).thenReturn(to_async(V10CredentialExchangeListResult(results=[record])))

    records = await IssuerV1.get_records(
        mock_agent_controller, connection_id=record.connection_id
    )

    assert len(records) == 1
    assert_that(map(lambda c: c.credential_id, records)).contains(
        f"v1-{record.credential_exchange_id}",
    )


@pytest.mark.anyio
async def test_get_record(mock_agent_controller: AcaPyClient):
    v1_record = v1_credential_exchange_records[0]

    when(mock_agent_controller.issue_credential_v1_0).get_record(
        cred_ex_id=v1_record.credential_exchange_id
    ).thenReturn(to_async(v1_record))

    record = await IssuerV1.get_record(
        mock_agent_controller, credential_exchange_id=v1_record.credential_exchange_id
    )

    assert record.credential_definition_id == v1_record.credential_definition_id
    assert record.created_at == v1_record.created_at
    assert record.role == v1_record.role
    assert record.updated_at == v1_record.updated_at
    assert record.schema_id == v1_record.schema_id
    assert record.state == "offer-sent"
    assert record.connection_id == v1_record.connection_id
    assert record.attributes == {
        attr.name: attr.value
        for attr in v1_record.credential_proposal_dict.credential_proposal.attributes
    }


@pytest.mark.anyio
async def test_delete_credential_exchange_with_credential(
    mock_agent_controller: AcaPyClient,
):
    with_credential_id = v1_credential_exchange_records[1]

    when(mock_agent_controller.issue_credential_v1_0).get_record(
        cred_ex_id=with_credential_id.credential_exchange_id
    ).thenReturn(to_async(with_credential_id))
    when(mock_agent_controller.issue_credential_v1_0).delete_record(
        cred_ex_id=with_credential_id.credential_exchange_id
    ).thenReturn(to_async())
    when(mock_agent_controller.credentials).delete_record(
        credential_id=with_credential_id.credential_id
    ).thenReturn(to_async())
    await IssuerV1.delete_credential(
        mock_agent_controller,
        credential_exchange_id=with_credential_id.credential_exchange_id,
    )


@pytest.mark.anyio
async def test_delete_credential_exchange_without_credential(
    mock_agent_controller: AcaPyClient,
):
    without_credential_id = v1_credential_exchange_records[0]
    when(mock_agent_controller.issue_credential_v1_0).get_record(
        cred_ex_id=without_credential_id.credential_exchange_id
    ).thenReturn(to_async(without_credential_id))
    when(mock_agent_controller.issue_credential_v1_0).delete_record(
        cred_ex_id=without_credential_id.credential_exchange_id
    ).thenReturn(to_async())
    await IssuerV1.delete_credential(
        mock_agent_controller,
        credential_exchange_id=without_credential_id.credential_exchange_id,
    )


@pytest.mark.anyio
async def test_send_credential(mock_agent_controller: AcaPyClient):
    record = v1_credential_exchange_records[0]

    credential = CredentialWithConnection(
        connection_id=record.connection_id,
        cred_def_id=record.credential_definition_id,
        attributes={
            attr.name: attr.value
            for attr in record.credential_proposal_dict.credential_proposal.attributes
        },
    )

    when(mock_agent_controller.issue_credential_v1_0).issue_credential_automated(
        ...
    ).thenReturn(to_async(record))

    credential_exchange = await IssuerV1.send_credential(
        mock_agent_controller, credential
    )

    assert (
        credential_exchange.credential_definition_id == record.credential_definition_id
    )
    assert credential_exchange.created_at == record.created_at
    assert credential_exchange.role == record.role
    assert credential_exchange.updated_at == record.updated_at
    assert credential_exchange.schema_id == record.schema_id
    assert credential_exchange.state == "offer-sent"
    assert credential_exchange.connection_id == record.connection_id
    assert credential_exchange.attributes == {
        attr.name: attr.value
        for attr in record.credential_proposal_dict.credential_proposal.attributes
    }


@pytest.mark.anyio
async def test_store_credential(mock_agent_controller: AcaPyClient):
    v1_record = v1_credential_exchange_records[0]

    when(mock_agent_controller.issue_credential_v1_0).store_credential(
        cred_ex_id=v1_record.credential_exchange_id,
        body=V10CredentialStoreRequest(credential_id=None),
    ).thenReturn(to_async(v1_record))

    credential_exchange = await IssuerV1.store_credential(
        mock_agent_controller, credential_exchange_id=v1_record.credential_exchange_id
    )

    assert credential_exchange.credential_id == f"v1-{v1_record.credential_exchange_id}"


@pytest.mark.anyio
async def test_request_credential(mock_agent_controller: AcaPyClient):
    v1_record = v1_credential_exchange_records[0]

    when(mock_agent_controller.issue_credential_v1_0).send_request(
        cred_ex_id=v1_record.credential_exchange_id
    ).thenReturn(to_async(v1_record))

    credential_exchange = await IssuerV1.request_credential(
        mock_agent_controller, credential_exchange_id=v1_record.credential_exchange_id
    )

    assert credential_exchange.credential_id == f"v1-{v1_record.credential_exchange_id}"
