import pytest
import mockito
from app.tests.util.client_fixtures import (
    member_admin_acapy_client,
    member_admin_client,
    yoma_acapy_client,
    yoma_client,
    ecosystem_admin_acapy_client,
    ecosystem_admin_client,
)
from app.tests.util.client import get_mock_agent_controller
from app.tests.util.member_personas import (
    alice_member_client,
    bob_and_alice_connection,
    bob_and_alice_public_did,
    bob_member_client,
    alice_acapy_client,
    bob_acapy_client,
)
from app.tests.util.ecosystem_personas import (
    faber_client,
    faber_and_alice_connection,
    faber_acapy_client,
)


@pytest.fixture
def mock_agent_controller():
    return get_mock_agent_controller()


@pytest.fixture(autouse=True)
def run_around_tests():
    yield

    # After each test, unstub all stubbed methods
    mockito.unstub()
