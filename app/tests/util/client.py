from typing import Any, Optional
from aries_cloudcontroller.acapy_client import AcaPyClient
from httpx import AsyncClient

from .constants import (
    ECOSYSTEM_FASTAPI_ENDPOINT,
    YOMA_FASTAPI_ENDPOINT,
    YOMA_ACAPY_API_KEY,
    MEMBER_FASTAPI_ENDPOINT,
    MEMBER_ACAPY_API_KEY,
)
from app.constants import (
    ECOSYSTEM_AGENT_API_KEY,
    ECOSYSTEM_AGENT_URL,
    YOMA_AGENT_URL,
    MEMBER_AGENT_URL,
)

# YOMA


def yoma_client(*, app: Optional[Any] = None):
    return AsyncClient(
        base_url=YOMA_FASTAPI_ENDPOINT,
        timeout=60.0,
        app=app,
        headers={
            "x-api-key": f"yoma.{YOMA_ACAPY_API_KEY}",
            "content-type": "application/json",
        },
    )


def yoma_acapy_client():
    return AcaPyClient(
        base_url=YOMA_AGENT_URL,
        api_key=YOMA_ACAPY_API_KEY,
    )


# MEMBER ADMIN


def member_admin_client(*, app: Optional[Any] = None):
    return AsyncClient(
        base_url=MEMBER_FASTAPI_ENDPOINT,
        timeout=60.0,
        app=app,
        headers={
            "x-api-key": f"member-admin.{MEMBER_ACAPY_API_KEY}",
            "content-type": "application/json",
        },
    )


def member_admin_acapy_client():
    return AcaPyClient(
        base_url=MEMBER_AGENT_URL,
        api_key=MEMBER_ACAPY_API_KEY,
    )


# MEMBER


def member_client(*, token: str, app: Optional[Any] = None):
    return AsyncClient(
        base_url=MEMBER_FASTAPI_ENDPOINT,
        timeout=60.0,
        app=app,
        headers={
            "x-api-key": f"member.{token}",
            "content-type": "application/json",
        },
    )


def member_acapy_client(*, token: str):
    return AcaPyClient(
        base_url=MEMBER_AGENT_URL, api_key=MEMBER_ACAPY_API_KEY, tenant_jwt=token
    )


# ECOSYSTEM ADMIN


def ecosystem_admin_client(*, app: Optional[Any] = None):
    return AsyncClient(
        base_url=ECOSYSTEM_FASTAPI_ENDPOINT,
        timeout=60.0,
        app=app,
        headers={
            "x-api-key": f"ecosystem-admin.{ECOSYSTEM_AGENT_API_KEY}",
            "content-type": "application/json",
        },
    )


def ecosystem_admin_acapy_client():
    return AcaPyClient(
        base_url=ECOSYSTEM_AGENT_URL,
        api_key=ECOSYSTEM_AGENT_API_KEY,
    )
