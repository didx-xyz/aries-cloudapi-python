import pytest
import mockito
from app.tests.util.client_fixtures import (
    governance_acapy_client,
    governance_client,
    tenant_admin_acapy_client,
    tenant_admin_client,
)
from app.tests.util.member_personas import (
    alice_acapy_client,
    alice_bob_connect_multi,
    alice_member_client,
    alice_tenant,
    bob_acapy_client,
    bob_and_alice_connection,
    bob_and_alice_public_did,
    bob_member_client,
    bob_multi_use_invitation,
)
from app.tests.util.ecosystem_personas import (
    acme_acapy_client,
    acme_and_alice_connection,
    acme_client,
    acme_tenant,
    faber_acapy_client,
    faber_and_alice_connection,
    faber_client,
)
from app.webhook_listener import Webhooks
from tests.fixtures import mock_agent_controller


@pytest.fixture(autouse=True)
def run_around_tests():
    yield

    # After each test, unstub all stubbed methods
    mockito.unstub()


@pytest.fixture(autouse=True)
async def shutdown_webhooks_listener():
    yield

    await Webhooks.shutdown()
