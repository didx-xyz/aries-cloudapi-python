import pytest
from app.tests.util.member_personas import alice_member_client, alice_tenant


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
