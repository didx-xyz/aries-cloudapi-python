import pytest
from aries_cloudcontroller import AcaPyClient

from app.dependencies.auth import Role
from shared import GOVERNANCE_ACAPY_API_KEY, TENANT_ACAPY_API_KEY


@pytest.mark.anyio
async def test_governance_agent(governance_acapy_client: AcaPyClient):
    assert isinstance(governance_acapy_client, AcaPyClient)
    assert governance_acapy_client.base_url == Role.GOVERNANCE.agent_type.base_url
    assert (
        governance_acapy_client.client.headers["x-api-key"] == GOVERNANCE_ACAPY_API_KEY
    )
    assert "Authorization" not in governance_acapy_client.client.headers


@pytest.mark.anyio
async def test_tenant_agent(alice_acapy_client: AcaPyClient):
    assert isinstance(alice_acapy_client, AcaPyClient)
    assert alice_acapy_client.base_url == Role.TENANT.agent_type.base_url
    assert "Bearer " in alice_acapy_client.client.headers["Authorization"]
    assert alice_acapy_client.client.headers["x-api-key"] == TENANT_ACAPY_API_KEY


@pytest.mark.anyio
async def test_tenant_admin_agent(tenant_admin_acapy_client):
    assert isinstance(tenant_admin_acapy_client, AcaPyClient)
    assert tenant_admin_acapy_client.client.headers["x-api-key"] == TENANT_ACAPY_API_KEY
    assert "Authorization" not in tenant_admin_acapy_client.client.headers
