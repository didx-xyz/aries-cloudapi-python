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


def governance_client(*, app: Optional[Any] = None):
    return AsyncClient(
        base_url=GOVERNANCE_FASTAPI_ENDPOINT,
        timeout=TEST_CLIENT_TIMEOUT,
        app=app,
        headers={
            "x-api-key": f"governance.{GOVERNANCE_ACAPY_API_KEY}",
            "content-type": "application/json",
        },
        transport=AsyncHTTPTransport(retries=3),
    )


def governance_acapy_client():
    return AcaPyClient(
        base_url=GOVERNANCE_AGENT_URL,
        api_key=GOVERNANCE_ACAPY_API_KEY,
    )


# TENANT ADMIN


def tenant_admin_client(*, app: Optional[Any] = None):
    return AsyncClient(
        base_url=TENANT_FASTAPI_ENDPOINT,
        timeout=TEST_CLIENT_TIMEOUT,
        app=app,
        headers={
            "x-api-key": f"tenant-admin.{TENANT_ACAPY_API_KEY}",
            "content-type": "application/json",
        },
        transport=AsyncHTTPTransport(retries=3),
    )


def tenant_admin_acapy_client():
    return AcaPyClient(
        base_url=TENANT_AGENT_URL,
        api_key=TENANT_ACAPY_API_KEY,
    )


# TENANT


def tenant_client(*, token: str, app: Optional[Any] = None):
    return AsyncClient(
        base_url=TENANT_FASTAPI_ENDPOINT,
        timeout=TEST_CLIENT_TIMEOUT,
        app=app,
        headers={
            "x-api-key": token,
            "content-type": "application/json",
        },
    )


def tenant_acapy_client(*, token: str):
    return AcaPyClient(
        base_url=TENANT_AGENT_URL,
        api_key=TENANT_ACAPY_API_KEY,
        tenant_jwt=token,
    )
