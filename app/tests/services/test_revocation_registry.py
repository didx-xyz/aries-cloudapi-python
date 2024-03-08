import pytest
from aries_cloudcontroller import (
    AcaPyClient,
    ApiException,
    IssuerRevRegRecord,
    RevokeRequest,
    RevRegCreateRequest,
    RevRegResult,
    TransactionRecord,
    TxnOrRevRegResult,
    V10CredentialExchange,
    V20CredExRecordDetail,
    V20CredExRecordIndy,
)
from mockito import when

import app.services.revocation_registry as rg
from app.exceptions import CloudApiException
from app.tests.util.mock import to_async

cred_def_id = "VagGATdBsVdBeFKeoYPe7H:3:CL:141:5d211963-3478-4de4-b8b6-9072759a71c8"
cred_ex_id = "5mJRavkcQFrqgKqKKZua3z:3:CL:30:tag"
cred_id = "c7c909f4-f670-49bd-9d81-53fba6bb23b8"
max_cred_num = 32767
revocation_registry_id = (
    "VagGATdBsVdBeFKeoYPe7H:4:VagGATdBsVdBeFKeoYPe7H:3:CL:141:"
    "QIOPN:CL_ACCUM:5d211963-3478-4de4-b8b6-9072759a71c8"
)
conn_id = "12345"
transaction_id = "1234"


@pytest.mark.anyio
async def test_get_active_revocation_registry_for_credential(
    mock_agent_controller: AcaPyClient,
):
    # Success
    when(mock_agent_controller.revocation).get_active_registry_for_cred_def(
        cred_def_id=cred_def_id
    ).thenReturn(
        to_async(
            RevRegResult(
                result=IssuerRevRegRecord(
                    cred_def_id=cred_def_id, max_cred_num=max_cred_num
                )
            )
        )
    )
    get_active_revocation_registry_for_credential_result = (
        await rg.get_active_revocation_registry_for_credential(
            controller=mock_agent_controller, credential_definition_id=cred_def_id
        )
    )

    assert isinstance(
        get_active_revocation_registry_for_credential_result, IssuerRevRegRecord
    )
    assert (
        get_active_revocation_registry_for_credential_result.cred_def_id == cred_def_id
    )
    assert (
        get_active_revocation_registry_for_credential_result.max_cred_num
        == max_cred_num
    )

    # Fail
    with pytest.raises(
        CloudApiException, match="Error retrieving revocation registry"
    ) as exc:
        when(mock_agent_controller.revocation).get_active_registry_for_cred_def(
            cred_def_id=cred_def_id
        ).thenReturn(to_async(None))
        await rg.get_active_revocation_registry_for_credential(
            mock_agent_controller, credential_definition_id=cred_def_id
        )
        assert exc.value.status_code == 500


@pytest.mark.anyio
async def test_revoke_credential(mock_agent_controller: AcaPyClient):
    # Success
    when(mock_agent_controller.revocation).revoke_credential(
        body=RevokeRequest(cred_ex_id=cred_id, publish=False)
    ).thenReturn(to_async({}))

    revoke_credential_result = await rg.revoke_credential(
        controller=mock_agent_controller,
        credential_definition_id=cred_def_id,
        credential_exchange_id=cred_id,
        auto_publish_to_ledger=False,
    )

    assert revoke_credential_result is None


@pytest.mark.anyio
async def test_get_credential_definition_id_from_exchange_id(
    mock_agent_controller: AcaPyClient,
):
    # Success v1
    when(mock_agent_controller.issue_credential_v1_0).get_record(
        cred_ex_id=cred_ex_id
    ).thenReturn(
        to_async(
            V10CredentialExchange(
                credential_exchange_id=cred_ex_id, credential_definition_id=cred_def_id
            )
        )
    )

    get_credential_definition_id_from_exchange_id_result = (
        await rg.get_credential_definition_id_from_exchange_id(
            controller=mock_agent_controller, credential_exchange_id=cred_ex_id
        )
    )

    assert get_credential_definition_id_from_exchange_id_result
    assert isinstance(get_credential_definition_id_from_exchange_id_result, str)
    assert get_credential_definition_id_from_exchange_id_result == cred_def_id

    # Success v2
    when(mock_agent_controller.issue_credential_v1_0).get_record(
        cred_ex_id=cred_ex_id
    ).thenRaise(ApiException())
    when(mock_agent_controller.issue_credential_v2_0).get_record(
        cred_ex_id=cred_ex_id
    ).thenReturn(
        to_async(
            V20CredExRecordDetail(
                indy=V20CredExRecordIndy(rev_reg_id=revocation_registry_id)
            )
        )
    )

    get_credential_definition_id_from_exchange_id_result = (
        await rg.get_credential_definition_id_from_exchange_id(
            controller=mock_agent_controller, credential_exchange_id=cred_ex_id
        )
    )

    assert get_credential_definition_id_from_exchange_id_result
    assert isinstance(get_credential_definition_id_from_exchange_id_result, str)
    assert get_credential_definition_id_from_exchange_id_result == cred_def_id

    # Not found
    when(mock_agent_controller.issue_credential_v1_0).get_record(
        cred_ex_id=cred_ex_id
    ).thenRaise(ApiException())
    when(mock_agent_controller.issue_credential_v2_0).get_record(
        cred_ex_id=cred_ex_id
    ).thenRaise(ApiException())

    get_credential_definition_id_from_exchange_id_result = (
        await rg.get_credential_definition_id_from_exchange_id(
            controller=mock_agent_controller, credential_exchange_id=cred_ex_id
        )
    )

    assert get_credential_definition_id_from_exchange_id_result is None
