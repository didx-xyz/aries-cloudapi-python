from typing import Any, Dict, Optional

from aries_cloudcontroller import AcaPyClient
from httpx import AsyncClient, AsyncHTTPTransport

from app.constants import GOVERNANCE_AGENT_URL, TENANT_AGENT_URL
from app.tests.util.constants import (
    GOVERNANCE_ACAPY_API_KEY,
    GOVERNANCE_FASTAPI_ENDPOINT,
    TENANT_ACAPY_API_KEY,
    TENANT_FASTAPI_ENDPOINT,
)

TEST_CLIENT_TIMEOUT = 300
MAX_NUM_RETRIES = 3


def get_common_settings(api_key: str, app: Optional[Any] = None) -> Dict[str, Any]:
    return {
        "timeout": TEST_CLIENT_TIMEOUT,
        "app": app,
        "headers": {
            "x-api-key": api_key,
            "content-type": "application/json",
        },
        "transport": AsyncHTTPTransport(retries=MAX_NUM_RETRIES),
    }


# Governance Clients
def governance_client(*, app: Optional[Any] = None):
    settings = get_common_settings(f"governance.{GOVERNANCE_ACAPY_API_KEY}", app)
    return AsyncClient(base_url=GOVERNANCE_FASTAPI_ENDPOINT, **settings)


def governance_acapy_client():
    return AcaPyClient(base_url=GOVERNANCE_AGENT_URL, api_key=GOVERNANCE_ACAPY_API_KEY)


# Tenant Admin Clients
def tenant_admin_client(*, app: Optional[Any] = None):
    settings = get_common_settings(f"tenant-admin.{TENANT_ACAPY_API_KEY}", app)
    return AsyncClient(base_url=TENANT_FASTAPI_ENDPOINT, **settings)


def tenant_admin_acapy_client():
    return AcaPyClient(base_url=TENANT_AGENT_URL, api_key=TENANT_ACAPY_API_KEY)


# Tenant Clients
def tenant_client(*, token: str, app: Optional[Any] = None):
    settings = get_common_settings(token, app)
    return AsyncClient(base_url=TENANT_FASTAPI_ENDPOINT, **settings)


def tenant_acapy_client(*, token: str):
    return AcaPyClient(
        base_url=TENANT_AGENT_URL,
        api_key=TENANT_ACAPY_API_KEY,
        tenant_jwt=token,
    )
