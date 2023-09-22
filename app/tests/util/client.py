from typing import Any, Dict, Optional

from aries_cloudcontroller import AcaPyClient
from httpx import AsyncHTTPTransport

from shared import (
    GOVERNANCE_ACAPY_API_KEY,
    GOVERNANCE_AGENT_URL,
    GOVERNANCE_FASTAPI_ENDPOINT,
    MAX_NUM_RETRIES,
    TENANT_ACAPY_API_KEY,
    TENANT_AGENT_URL,
    TENANT_FASTAPI_ENDPOINT,
    TEST_CLIENT_TIMEOUT,
    RichAsyncClient,
)


def get_common_settings(api_key: str, app: Optional[Any] = None) -> Dict[str, Any]:
    return {
        "timeout": TEST_CLIENT_TIMEOUT,
        "app": app,
        "headers": {
            "x-api-key": api_key,
            "content-type": "application/json",
        },
        "transport": AsyncHTTPTransport(retries=3),
    }


# Governance Clients
def get_governance_client(*, app: Optional[Any] = None) -> RichAsyncClient:
    settings = get_common_settings(f"governance.{GOVERNANCE_ACAPY_API_KEY}", app)
    return RichAsyncClient(
        base_url=GOVERNANCE_FASTAPI_ENDPOINT, name="Governance", **settings
    )


def get_governance_acapy_client() -> AcaPyClient:
    return AcaPyClient(base_url=GOVERNANCE_AGENT_URL, api_key=GOVERNANCE_ACAPY_API_KEY)


# Tenant Admin Clients
def get_tenant_admin_client(*, app: Optional[Any] = None) -> RichAsyncClient:
    settings = get_common_settings(f"tenant-admin.{TENANT_ACAPY_API_KEY}", app)
    return RichAsyncClient(
        base_url=TENANT_FASTAPI_ENDPOINT, name="Tenant Admin", **settings
    )


def get_tenant_admin_acapy_client() -> AcaPyClient:
    return AcaPyClient(base_url=TENANT_AGENT_URL, api_key=TENANT_ACAPY_API_KEY)


# Tenant Clients
def get_tenant_client(*, token: str, app: Optional[Any] = None) -> RichAsyncClient:
    settings = get_common_settings(token, app)
    return RichAsyncClient(base_url=TENANT_FASTAPI_ENDPOINT, name="Tenant", **settings)


def get_tenant_acapy_client(*, token: str) -> AcaPyClient:
    return AcaPyClient(
        base_url=TENANT_AGENT_URL,
        api_key=TENANT_ACAPY_API_KEY,
        tenant_jwt=token,
    )
