import pytest

# flake8: noqa
# pylint: disable=unused-import
from app.tests.e2e.conftest import governance_public_did
from app.tests.util.ecosystem_connections import bob_and_alice_connection
from app.tests.util.member_acapy_clients import governance_acapy_client
from app.tests.util.member_async_clients import (
    alice_member_client,
    bob_member_client,
    governance_client,
)
from app.tests.util.member_wallets import alice_tenant


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
