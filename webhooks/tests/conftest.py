import pytest

# pylint: disable=unused-import
from app.tests.util.ecosystem_personas import acme_and_alice_connection, acme_tenant
from app.tests.util.member_personas import alice_member_client, alice_tenant


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
