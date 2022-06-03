from typing import Any, Optional
from aries_cloudcontroller import (
    ConnectionApi,
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
    SchemaApi,
)
from httpx import AsyncClient, AsyncHTTPTransport
from mockito import mock

from .constants import (
    GOVERNANCE_FASTAPI_ENDPOINT,
    GOVERNANCE_ACAPY_API_KEY,
    TENANT_ACAPY_API_KEY,
    TENANT_FASTAPI_ENDPOINT,
)
from app.constants import (
    GOVERNANCE_AGENT_URL,
    TENANT_AGENT_URL,
)

# GOVERNANCE


def get_mock_agent_controller() -> AcaPyClient:
    controller = mock(AcaPyClient)
    controller.wallet = mock(WalletApi)
    controller.ledger = mock(LedgerApi)
    controller.connection = mock(ConnectionApi)
    controller.issue_credential_v1_0 = mock(IssueCredentialV10Api)
    controller.issue_credential_v2_0 = mock(IssueCredentialV20Api)
    controller.present_proof_v1_0 = mock(PresentProofV10Api)
    controller.present_proof_v2_0 = mock(PresentProofV20Api)
    controller.credentials = mock(CredentialsApi)
    controller.out_of_band = mock(OutOfBandApi)
    controller.endorse_transaction = mock(EndorseTransactionApi)
    controller.schema = mock(SchemaApi)
    return controller


def governance_client(*, app: Optional[Any] = None):
    return AsyncClient(
        base_url=GOVERNANCE_FASTAPI_ENDPOINT,
        timeout=60.0,
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
        timeout=60.0,
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
        timeout=60.0,
        app=app,
        headers={
            "x-api-key": token,
            "content-type": "application/json",
        },
    )


def tenant_acapy_client(*, token: str):
    return AcaPyClient(
        base_url=TENANT_AGENT_URL, api_key=TENANT_ACAPY_API_KEY, tenant_jwt=token
    )
