from aries_cloudcontroller import (
    AcaPyClient,
    IssuerRevRegRecord,
    RevRegCreateRequest,
    RevRegResult,
)

import pytest
from mockito import when
from app.error.cloud_api_error import CloudApiException

import app.facades.revocation_registry as rg
from tests.util.mock import get


@pytest.mark.asyncio
async def test_create_revocation_registry(mock_agent_controller: AcaPyClient):
    cred_def_id = "5mJRavkcQFrqgKqKKZua3z:3:CL:30:tag"
    max_cred_num = 32767
    when(mock_agent_controller.revocation).create_registry(
        body=RevRegCreateRequest(
            credential_definition_id=cred_def_id, max_cred_num=max_cred_num
        )
    ).thenReturn(
        get(
            RevRegResult(
                result=IssuerRevRegRecord(
                    cred_def_id=cred_def_id, max_cred_num=max_cred_num
                )
            )
        )
    )
    # Success
    create_registry_result = await rg.create_revocation_registry(
        mock_agent_controller, credential_definition_id=cred_def_id
    )

    assert isinstance(create_registry_result, IssuerRevRegRecord)
    assert create_registry_result.cred_def_id == cred_def_id
    assert create_registry_result.max_cred_num == max_cred_num

    # Failure
    with pytest.raises(
        CloudApiException,
        match="Error creating revocation registry for credential with ID",
    ) as exc:
        when(mock_agent_controller.revocation).create_registry(
            body=RevRegCreateRequest(
                credential_definition_id=cred_def_id, max_cred_num=max_cred_num
            )
        ).thenReturn(get(None))
        await rg.create_revocation_registry(
            mock_agent_controller, credential_definition_id=cred_def_id
        )
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_get_active_revocation_registry_for_credential():
    pass


@pytest.mark.asyncio
async def test_get_credential_revocation_status():
    pass


@pytest.mark.asyncio
async def test_publish_revocation_registry_on_ledger():
    pass


@pytest.mark.asyncio
async def test_publish_revocation_entry_to_ledger():
    pass


@pytest.mark.asyncio
async def test_revoke_credential():
    pass
