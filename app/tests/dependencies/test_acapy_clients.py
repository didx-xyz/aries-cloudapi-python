from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.dependencies.acapy_clients import (
    AcaPyAuthVerified,
    AcaPyClient,
    Role,
    client_from_auth,
    get_governance_controller,
    get_tenant_admin_controller,
    get_tenant_controller,
)
from app.dependencies.auth import AcaPyAuth


# Mock classes and data as needed
class MockRole:
    GOVERNANCE = Role.GOVERNANCE
    TENANT_ADMIN = Role.TENANT_ADMIN
    TENANT = Role.TENANT


def test_get_governance_controller():
    with patch("app.dependencies.acapy_clients.AcaPyClient") as MockAcaPyClient:
        get_governance_controller()
        MockAcaPyClient.assert_called_with(
            base_url=MockRole.GOVERNANCE.agent_type.base_url,
            api_key=MockRole.GOVERNANCE.agent_type.x_api_key,
        )


def test_get_tenant_admin_controller():
    with patch("app.dependencies.acapy_clients.AcaPyClient") as MockAcaPyClient:
        get_tenant_admin_controller()
        MockAcaPyClient.assert_called_with(
            base_url=MockRole.TENANT_ADMIN.agent_type.base_url,
            api_key=MockRole.TENANT_ADMIN.agent_type.x_api_key,
        )


def test_get_tenant_controller():
    auth_token = "fake-jwt-token"
    with patch("app.dependencies.acapy_clients.AcaPyClient") as MockAcaPyClient:
        get_tenant_controller(auth_token)
        MockAcaPyClient.assert_called_with(
            base_url=MockRole.TENANT.agent_type.base_url,
            api_key=MockRole.TENANT.agent_type.x_api_key,
            tenant_jwt=auth_token,
        )


@pytest.mark.parametrize(
    "is_multitenant,is_admin",
    [
        (True, False),  # Multi-tenant but not admin
        (False, True),  # Admin but not multi-tenant
        (False, False),  # Neither admin nor multi-tenant
    ],
)
@pytest.mark.anyio
async def test_client_from_auth(is_multitenant, is_admin):
    auth = AcaPyAuthVerified(token="dummy-token", role=Mock(), wallet_id=Mock())
    auth.role.is_multitenant = is_multitenant
    auth.role.is_admin = is_admin
    auth.role.agent_type = Mock(x_api_key="api-key", base_url="base-url")

    client = client_from_auth(auth)
    assert isinstance(client, AcaPyClient)


def test_client_from_auth_missing_auth():
    with pytest.raises(HTTPException) as exc_info:
        client_from_auth(None)
    assert exc_info.value.status_code == 403

    with pytest.raises(HTTPException) as exc_info:
        client_from_auth(AcaPyAuth(token="", role=Role.TENANT))
    assert exc_info.value.status_code == 403
