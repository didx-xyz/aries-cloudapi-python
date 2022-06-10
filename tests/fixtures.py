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
    SchemaApi,
    WalletApi,
)
from mockito import mock


async def noop():
    return None


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
    controller.__aexit__ = noop
    return controller


@pytest.fixture
def mock_agent_controller():
    return get_mock_agent_controller()
