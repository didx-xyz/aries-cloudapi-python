import pytest
from aries_cloudcontroller import (
    AcaPyClient,
    ConnectionApi,
    CredentialsApi,
    EndorseTransactionApi,
    IssueCredentialV10Api,
    IssueCredentialV20Api,
    LedgerApi,
    OutOfBandApi,
    PresentProofV10Api,
    PresentProofV20Api,
    RevocationApi,
    SchemaApi,
    WalletApi,
)
from mockito import mock


async def noop():
    return None


def get_mock_agent_controller() -> AcaPyClient:
    controller = mock(AcaPyClient)
    controller.__aexit__ = noop
    controller.connection = mock(ConnectionApi)
    controller.credentials = mock(CredentialsApi)
    controller.endorse_transaction = mock(EndorseTransactionApi)
    controller.issue_credential_v1_0 = mock(IssueCredentialV10Api)
    controller.issue_credential_v2_0 = mock(IssueCredentialV20Api)
    controller.ledger = mock(LedgerApi)
    controller.out_of_band = mock(OutOfBandApi)
    controller.present_proof_v1_0 = mock(PresentProofV10Api)
    controller.present_proof_v2_0 = mock(PresentProofV20Api)
    controller.revocation = mock(RevocationApi)
    controller.schema = mock(SchemaApi)
    controller.wallet = mock(WalletApi)
    return controller


class MockContextManagedController:
    def __init__(self, controller):
        self.controller = controller

    async def __aenter__(self):
        return self.controller

    async def __aexit__(self, exc_type, exc, tb):
        pass


@pytest.fixture
def mock_agent_controller():
    return get_mock_agent_controller()


@pytest.fixture
def mock_context_managed_controller():
    return MockContextManagedController

