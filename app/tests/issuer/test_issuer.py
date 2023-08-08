import pytest
from aries_cloudcontroller import AcaPyClient
from mockito import mock, verify, when
from pytest_mock import MockerFixture

import app.routes.issuer as test_module
from app.dependencies.auth import AcaPyAuth
from app.services.issuer.acapy_issuer_v1 import IssuerV1
from app.services.issuer.acapy_issuer_v2 import IssuerV2
from app.tests.util.mock import to_async
from shared.models.topics import CredentialExchange, IssueCredentialProtocolVersion
from shared.util.mock_agent_controller import MockContextManagedController


@pytest.mark.anyio
async def test_send_credential(
    mock_agent_controller: AcaPyClient,
    mock_context_managed_controller: MockContextManagedController,
    mock_tenant_auth: AcaPyAuth,
    mocker: MockerFixture,
):
    did = "did:sov:WgWxqztrNooG92RXvxSTWv"
    cred_def_id = "WgWxqztrNooG92RXvxSTWv:1:12345:tag"
    cred_ex = mock(CredentialExchange)

    mocker.patch.object(
        test_module,
        "client_from_auth",
        return_value=mock_context_managed_controller(mock_agent_controller),
    )

    when(test_module).assert_valid_issuer(...).thenReturn(to_async(True))
    when(test_module).schema_id_from_credential_definition_id(
        mock_agent_controller, cred_def_id
    ).thenReturn(to_async("schema_id"))
    when(IssuerV1).send_credential(...).thenReturn(to_async(cred_ex))
    when(test_module).assert_public_did(...).thenReturn(to_async(did))

    credential = test_module.SendCredential(
        protocol_version=IssueCredentialProtocolVersion.v1,
        connection_id="conn_id",
        cred_def_id=cred_def_id,
        attributes={"name": "John", "age": "23"},
    )

    result = await test_module.send_credential(credential, mock_tenant_auth)

    assert result is cred_ex
    verify(IssuerV1).send_credential(...)
    verify(test_module).schema_id_from_credential_definition_id(
        mock_agent_controller, cred_def_id
    )
    verify(test_module).assert_public_did(mock_agent_controller)
    verify(test_module).assert_valid_issuer(did, "schema_id")


@pytest.mark.anyio
async def test_get_credentials(
    mock_agent_controller: AcaPyClient,
    mock_context_managed_controller: MockContextManagedController,
    mock_tenant_auth: AcaPyAuth,
    mocker: MockerFixture,
):
    mocker.patch.object(
        test_module,
        "client_from_auth",
        return_value=mock_context_managed_controller(mock_agent_controller),
    )

    v1_records_no_conn_id = [mock(CredentialExchange), mock(CredentialExchange)]
    v2_records_no_conn_id = [mock(CredentialExchange), mock(CredentialExchange)]

    v1_records = [mock(CredentialExchange)]
    v2_records = [mock(CredentialExchange)]

    with when(IssuerV1).get_records(...).thenReturn(
        to_async(v1_records_no_conn_id)
    ), when(IssuerV2).get_records(...).thenReturn(to_async(v2_records_no_conn_id)):
        result = await test_module.get_credentials(None, mock_tenant_auth)

        assert result == v1_records_no_conn_id + v2_records_no_conn_id

        verify(IssuerV1).get_records(
            controller=mock_agent_controller, connection_id=None
        )
        verify(IssuerV2).get_records(
            controller=mock_agent_controller, connection_id=None
        )

    with when(IssuerV1).get_records(...).thenReturn(to_async(v1_records)), when(
        IssuerV2
    ).get_records(...).thenReturn(to_async(v2_records)):
        result = await test_module.get_credentials("conn_id", mock_tenant_auth)

        assert result == v1_records + v2_records
        verify(IssuerV1).get_records(
            controller=mock_agent_controller, connection_id="conn_id"
        )
        verify(IssuerV2).get_records(
            controller=mock_agent_controller, connection_id="conn_id"
        )


@pytest.mark.anyio
async def test_get_credential(
    mock_agent_controller: AcaPyClient,
    mock_context_managed_controller: MockContextManagedController,
    mock_tenant_auth: AcaPyAuth,
    mocker: MockerFixture,
):
    mocker.patch.object(
        test_module,
        "client_from_auth",
        return_value=mock_context_managed_controller(mock_agent_controller),
    )

    v1_record = mock(CredentialExchange)
    v2_record = mock(CredentialExchange)

    with when(IssuerV1).get_record(...).thenReturn(to_async(v1_record)):
        result = await test_module.get_credential("v1-credential_id", mock_tenant_auth)

        assert result is v1_record

        verify(IssuerV1).get_record(
            controller=mock_agent_controller, credential_exchange_id="v1-credential_id"
        )

    with when(IssuerV2).get_record(...).thenReturn(to_async(v2_record)):
        result = await test_module.get_credential("v2-credential_id", mock_tenant_auth)

        assert result is v2_record
        verify(IssuerV2).get_record(
            controller=mock_agent_controller, credential_exchange_id="v2-credential_id"
        )


@pytest.mark.anyio
async def test_remove_credential(
    mock_agent_controller: AcaPyClient,
    mock_context_managed_controller: MockContextManagedController,
    mock_tenant_auth: AcaPyAuth,
    mocker: MockerFixture,
):
    mocker.patch.object(
        test_module,
        "client_from_auth",
        return_value=mock_context_managed_controller(mock_agent_controller),
    )

    v1_record = mock(CredentialExchange)
    v2_record = mock(CredentialExchange)

    with when(IssuerV1).delete_credential(...).thenReturn(to_async(v1_record)):
        await test_module.remove_credential("v1-credential_id", mock_tenant_auth)

        verify(IssuerV1).delete_credential(
            controller=mock_agent_controller, credential_exchange_id="v1-credential_id"
        )
    with when(IssuerV2).delete_credential(...).thenReturn(to_async(v2_record)):
        await test_module.remove_credential("v2-credential_id", mock_tenant_auth)

        verify(IssuerV2).delete_credential(
            controller=mock_agent_controller, credential_exchange_id="v2-credential_id"
        )


@pytest.mark.anyio
async def test_request_credential(
    mock_agent_controller: AcaPyClient,
    mock_context_managed_controller: MockContextManagedController,
    mock_tenant_auth: AcaPyAuth,
    mocker: MockerFixture,
):
    mocker.patch.object(
        test_module,
        "client_from_auth",
        return_value=mock_context_managed_controller(mock_agent_controller),
    )

    v1_record = mock(CredentialExchange)
    v2_record = mock(CredentialExchange)

    v1_record.credential_definition_id = "WgWxqztrNooG92RXvxSTWv:other:parts"
    v1_record.schema_id = "schema_id1"

    v2_record.credential_definition_id = "WgWxqztrNooG92RXvxSTWv:other:parts"
    v2_record.schema_id = "schema_id2"

    with when(IssuerV1).request_credential(...).thenReturn(to_async(v1_record)), when(
        test_module
    ).assert_valid_issuer(...).thenReturn(to_async(True)), when(IssuerV1).get_record(
        ...
    ).thenReturn(
        to_async(v1_record)
    ):
        await test_module.request_credential("v1-credential_id", mock_tenant_auth)

        verify(IssuerV1).request_credential(
            controller=mock_agent_controller, credential_exchange_id="v1-credential_id"
        )
        verify(test_module).assert_valid_issuer(
            "did:sov:WgWxqztrNooG92RXvxSTWv", "schema_id1"
        )

    with when(IssuerV2).request_credential(...).thenReturn(to_async(v2_record)), when(
        IssuerV2
    ).get_record(...).thenReturn(to_async(v2_record)), when(
        test_module
    ).assert_valid_issuer(
        ...
    ).thenReturn(
        to_async(True)
    ):
        await test_module.request_credential("v2-credential_id", mock_tenant_auth)

        verify(IssuerV2).request_credential(
            controller=mock_agent_controller, credential_exchange_id="v2-credential_id"
        )
        verify(test_module).assert_valid_issuer(
            "did:sov:WgWxqztrNooG92RXvxSTWv", "schema_id2"
        )


@pytest.mark.anyio
async def test_request_credential_x_no_schema_cred_def(
    mock_agent_controller: AcaPyClient,
    mock_tenant_auth: AcaPyAuth,
):
    v1_record = mock(CredentialExchange)

    v1_record.credential_definition_id = None
    v1_record.schema_id = None

    with when(IssuerV1).get_record(...).thenReturn(to_async(v1_record)), pytest.raises(
        Exception, match="Record has no credential definition or schema associated."
    ):
        await test_module.request_credential("v1-credential_id", mock_tenant_auth)

        verify(IssuerV1, times=0).request_credential(
            controller=mock_agent_controller, credential_exchange_id="credential_id"
        )
        verify(test_module, times=0).assert_valid_issuer(
            "did:sov:WgWxqztrNooG92RXvxSTWv", "schema_id1"
        )


@pytest.mark.anyio
async def test_store_credential(
    mock_agent_controller: AcaPyClient,
    mock_context_managed_controller: MockContextManagedController,
    mock_tenant_auth: AcaPyAuth,
    mocker: MockerFixture,
):
    mocker.patch.object(
        test_module,
        "client_from_auth",
        return_value=mock_context_managed_controller(mock_agent_controller),
    )

    v1_record = mock(CredentialExchange)
    v2_record = mock(CredentialExchange)

    when(IssuerV1).store_credential(...).thenReturn(to_async(v1_record))
    when(IssuerV2).store_credential(...).thenReturn(to_async(v2_record))

    await test_module.store_credential("v1-credential_id1", mock_tenant_auth)
    await test_module.store_credential("v2-credential_id2", mock_tenant_auth)

    verify(IssuerV1).store_credential(
        controller=mock_agent_controller, credential_exchange_id="v1-credential_id1"
    )
    verify(IssuerV2).store_credential(
        controller=mock_agent_controller, credential_exchange_id="v2-credential_id2"
    )
