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
    bob_multi_use_invitation,
    alice_bob_connect_multi,
    bob_and_alice_public_did,
    bob_member_client,
    alice_acapy_client,
    bob_acapy_client,
    alice_tenant,
)
from app.tests.util.ecosystem_personas import (
    faber_client,
    faber_and_alice_connection,
    faber_acapy_client,
    acme_client,
    acme_acapy_client,
    acme_and_alice_connection,
    acme_tenant,
)
from app.webhook_listener import Webhooks


@pytest.fixture
def mock_agent_controller():
    return get_mock_agent_controller()


@pytest.fixture(autouse=True)
def run_around_tests():
    yield

    # After each test, unstub all stubbed methods
    mockito.unstub()


@pytest.fixture(autouse=True)
async def shutdown_webhooks_listener():
    yield

    await Webhooks.shutdown()
