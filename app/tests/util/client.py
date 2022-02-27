from typing import Any, Optional
from aries_cloudcontroller import (
    LedgerApi,
    OutOfBandApi,
    WalletApi,
    AcaPyClient,
    IssueCredentialV10Api,
    IssueCredentialV20Api,
    PresentProofV20Api,
    PresentProofV10Api,
    CredentialsApi,
    EndorseTransactionApi,
)
from httpx import AsyncClient, AsyncHTTPTransport
from mockito import mock

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


def get_mock_agent_controller() -> AcaPyClient:
    controller = mock(AcaPyClient)
    controller.wallet = mock(WalletApi)
    controller.ledger = mock(LedgerApi)
    controller.issue_credential_v1_0 = mock(IssueCredentialV10Api)
    controller.issue_credential_v2_0 = mock(IssueCredentialV20Api)
    controller.present_proof_v1_0 = mock(PresentProofV10Api)
    controller.present_proof_v2_0 = mock(PresentProofV20Api)
    controller.credentials = mock(CredentialsApi)
    controller.out_of_band = mock(OutOfBandApi)
    controller.endorse_transaction = mock(EndorseTransactionApi)
    return controller


def yoma_client(*, app: Optional[Any] = None):
    return AsyncClient(
        base_url=YOMA_FASTAPI_ENDPOINT,
        timeout=60.0,
        app=app,
        headers={
            "x-api-key": f"yoma.{YOMA_ACAPY_API_KEY}",
            "content-type": "application/json",
        },
        transport=AsyncHTTPTransport(retries=3),
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
        transport=AsyncHTTPTransport(retries=3),
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
            "x-api-key": token,
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
