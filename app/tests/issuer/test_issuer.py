from typing import Any, Optional

import pytest
from aries_cloudcontroller import DID, AcaPyClient, DIDResult
from mockito import mock, verify, when

import app.generic.issuer.issuer as test_module
from app.generic.issuer.facades.acapy_issuer_v1 import IssuerV1
from app.generic.issuer.facades.acapy_issuer_v2 import IssuerV2
from app.generic.issuer.models import CredentialExchange, IssueCredentialProtocolVersion


# need this to handle the async with the mock
async def get(response: Optional[Any] = None):
    if response:
        return response


@pytest.mark.asyncio
async def test_send_credential(mock_agent_controller: AcaPyClient):
    did = "WgWxqztrNooG92RXvxSTWv"
    cred_ex = mock(CredentialExchange)

    when(test_module).assert_valid_issuer(...).thenReturn(get(True))
    when(test_module).write_credential_def(...).thenReturn(get("cred_def_id"))
    when(IssuerV1).send_credential(...).thenReturn(get(cred_ex))
    when(mock_agent_controller.wallet).get_public_did().thenReturn(
        get(DIDResult(result=DID(did=did)))
    )

    credential = test_module.SendCredential(
        protocol_version=IssueCredentialProtocolVersion.v1,
        connection_id="conn_id",
        schema_id="schema_id",
        attributes={"name": "John", "age": "23"},
    )

    result = await test_module.send_credential(credential, mock_agent_controller)

    assert result is cred_ex
    verify(IssuerV1).send_credential(...)
    verify(test_module).write_credential_def(mock_agent_controller, "schema_id")
    verify(mock_agent_controller.wallet).get_public_did()
    verify(test_module).assert_valid_issuer(f"did:sov:{did}", "schema_id")


@pytest.mark.asyncio
async def test_get_credentials(mock_agent_controller: AcaPyClient):
    v1_records_no_conn_id = [mock(CredentialExchange), mock(CredentialExchange)]
    v2_records_no_conn_id = [mock(CredentialExchange), mock(CredentialExchange)]

    v1_records = [mock(CredentialExchange)]
    v2_records = [mock(CredentialExchange)]

    with when(IssuerV1).get_records(...).thenReturn(get(v1_records_no_conn_id)), when(
        IssuerV2
    ).get_records(...).thenReturn(get(v2_records_no_conn_id)):
        result = await test_module.get_credentials(None, mock_agent_controller)

        assert result == v1_records_no_conn_id + v2_records_no_conn_id

        verify(IssuerV1).get_records(
            controller=mock_agent_controller, connection_id=None
        )
        verify(IssuerV2).get_records(
            controller=mock_agent_controller, connection_id=None
        )

    with when(IssuerV1).get_records(...).thenReturn(get(v1_records)), when(
        IssuerV2
    ).get_records(...).thenReturn(get(v2_records)):
        result = await test_module.get_credentials("conn_id", mock_agent_controller)

        assert result == v1_records + v2_records
        verify(IssuerV1).get_records(
            controller=mock_agent_controller, connection_id="conn_id"
        )
        verify(IssuerV2).get_records(
            controller=mock_agent_controller, connection_id="conn_id"
        )


@pytest.mark.asyncio
async def test_get_credential(mock_agent_controller: AcaPyClient):
    v1_record = mock(CredentialExchange)
    v2_record = mock(CredentialExchange)

    with when(IssuerV1).get_record(...).thenReturn(get(v1_record)):
        result = await test_module.get_credential(
            "v1-credential_id", mock_agent_controller
        )

        assert result is v1_record

        verify(IssuerV1).get_record(
            controller=mock_agent_controller, credential_exchange_id="credential_id"
        )

    with when(IssuerV2).get_record(...).thenReturn(get(v2_record)):
        result = await test_module.get_credential(
            "v2-credential_id", mock_agent_controller
        )

        assert result is v2_record
        verify(IssuerV2).get_record(
            controller=mock_agent_controller, credential_exchange_id="credential_id"
        )


@pytest.mark.asyncio
async def test_remove_credential(mock_agent_controller: AcaPyClient):
    v1_record = mock(CredentialExchange)
    v2_record = mock(CredentialExchange)

    with when(IssuerV1).delete_credential(...).thenReturn(get(v1_record)):
        await test_module.remove_credential("v1-credential_id", mock_agent_controller)

        verify(IssuerV1).delete_credential(
            controller=mock_agent_controller, credential_exchange_id="credential_id"
        )
    with when(IssuerV2).delete_credential(...).thenReturn(get(v2_record)):
        await test_module.remove_credential("v2-credential_id", mock_agent_controller)

        verify(IssuerV2).delete_credential(
            controller=mock_agent_controller, credential_exchange_id="credential_id"
        )


@pytest.mark.asyncio
async def test_request_credential(
    mock_agent_controller: AcaPyClient,
):
    v1_record = mock(CredentialExchange)
    v2_record = mock(CredentialExchange)

    v1_record.credential_definition_id = "WgWxqztrNooG92RXvxSTWv:other:parts"
    v1_record.schema_id = "schema_id1"

    v2_record.credential_definition_id = "WgWxqztrNooG92RXvxSTWv:other:parts"
    v2_record.schema_id = "schema_id2"

    with when(IssuerV1).request_credential(...).thenReturn(get(v1_record)), when(
        test_module
    ).assert_valid_issuer(...).thenReturn(get(True)), when(IssuerV1).get_record(
        ...
    ).thenReturn(
        get(v1_record)
    ):
        await test_module.request_credential("v1-credential_id", mock_agent_controller)

        verify(IssuerV1).request_credential(
            controller=mock_agent_controller, credential_exchange_id="credential_id"
        )
        verify(test_module).assert_valid_issuer(
            "did:sov:WgWxqztrNooG92RXvxSTWv", "schema_id1"
        )

    with when(IssuerV2).request_credential(...).thenReturn(get(v2_record)), when(
        IssuerV2
    ).get_record(...).thenReturn(get(v2_record)), when(test_module).assert_valid_issuer(
        ...
    ).thenReturn(
        get(True)
    ):
        await test_module.request_credential("v2-credential_id", mock_agent_controller)

        verify(IssuerV2).request_credential(
            controller=mock_agent_controller, credential_exchange_id="credential_id"
        )
        verify(test_module).assert_valid_issuer(
            "did:sov:WgWxqztrNooG92RXvxSTWv", "schema_id2"
        )


@pytest.mark.asyncio
async def test_request_credential_x_no_schema_cred_def(
    mock_agent_controller: AcaPyClient,
):
    v1_record = mock(CredentialExchange)

    v1_record.credential_definition_id = None
    v1_record.schema_id = None

    with when(IssuerV1).get_record(...).thenReturn(get(v1_record)), pytest.raises(
        Exception, match="Record has no credential definition or schema associated."
    ):
        await test_module.request_credential("v1-credential_id", mock_agent_controller)

        verify(IssuerV1, times=0).request_credential(
            controller=mock_agent_controller, credential_exchange_id="credential_id"
        )
        verify(test_module, times=0).assert_valid_issuer(
            "did:sov:WgWxqztrNooG92RXvxSTWv", "schema_id1"
        )


@pytest.mark.asyncio
async def test_store_credential(mock_agent_controller: AcaPyClient):
    v1_record = mock(CredentialExchange)
    v2_record = mock(CredentialExchange)

    when(IssuerV1).store_credential(...).thenReturn(get(v1_record))
    when(IssuerV2).store_credential(...).thenReturn(get(v2_record))

    await test_module.store_credential("v1-credential_id1", mock_agent_controller)
    await test_module.store_credential("v2-credential_id2", mock_agent_controller)

    verify(IssuerV1).store_credential(
        controller=mock_agent_controller, credential_exchange_id="credential_id1"
    )
    verify(IssuerV2).store_credential(
        controller=mock_agent_controller, credential_exchange_id="credential_id2"
    )
