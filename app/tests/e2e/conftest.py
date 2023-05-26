import pytest
from aries_cloudcontroller import AcaPyClient

from app.tests.util.ledger import create_public_did, has_public_did


# Governace should be provisioned with public did in all e2e tests
@pytest.fixture(autouse=True, scope="module")
async def governance_public_did(governance_acapy_client: AcaPyClient):
    if not await has_public_did(governance_acapy_client):
        await create_public_did(governance_acapy_client, set_public=True)
