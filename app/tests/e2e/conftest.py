import asyncio
from typing import Any
from aries_cloudcontroller import AcaPyClient
import pytest

from app.tests.e2e.test_fixtures import issue_credential_to_alice
from app.tests.util.ledger import create_public_did, has_public_did


@pytest.yield_fixture(autouse=True, scope="module")
def event_loop(request: Any):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Governace should be provisioned with public did in all e2e tests
@pytest.fixture(autouse=True, scope="module")
async def governance_public_did(governance_acapy_client: AcaPyClient):
    if not await has_public_did(governance_acapy_client):
        await create_public_did(governance_acapy_client, set_public=True)
