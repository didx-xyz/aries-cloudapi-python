from contextlib import asynccontextmanager

import pytest
from aries_cloudcontroller import (
    AcaPyClient,
    CredentialsApi,
    IssueCredentialV10Api,
    IssueCredentialV20Api,
    LedgerApi,
    WalletApi,
)
from httpx import AsyncClient
from mockito import mock

from app.dependencies import AcaPyAuth, Role, agent_role
from app.main import app
from app.tests.util.constants import YOMA_ACAPY_API_KEY

from app.tests.util.member_personas import (
    alice_member_client,
    bob_and_alice_connection,
    bob_member_client,
)
from app.tests.util.client_fixtures import (
    member_admin_acapy_client,
    member_admin_client,
    yoma_acapy_client,
    yoma_client,
)


@pytest.fixture
def mock_agent_controller():
    controller = mock(AcaPyClient)
    controller.wallet = mock(WalletApi)
    controller.ledger = mock(LedgerApi)
    controller.issue_credential_v1_0 = mock(IssueCredentialV10Api)
    controller.issue_credential_v2_0 = mock(IssueCredentialV20Api)
    controller.credentials = mock(CredentialsApi)
    return controller
