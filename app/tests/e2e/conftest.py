import pytest
from aries_cloudcontroller import AcaPyClient

from app.exceptions.cloud_api_error import CloudApiException
from app.facades.acapy_wallet import get_public_did
from app.facades.trust_registry import (
    Actor,
    actor_by_id,
    register_actor,
    remove_actor_by_id,
)

# pylint: disable=unused-import
from app.tests.e2e.test_fixtures import credential_definition_id  # noqa: F401
from app.tests.e2e.test_fixtures import credential_definition_id_revocable  # noqa: F401
from app.tests.e2e.test_fixtures import credential_exchange_id  # noqa: F401
from app.tests.e2e.test_fixtures import issue_credential_to_alice  # noqa: F401
from app.tests.e2e.test_fixtures import schema_definition  # noqa: F401
from app.tests.e2e.test_fixtures import schema_definition_alt  # noqa: F401
from app.tests.util.ledger import create_public_did
from app.tests.util.string import random_string


# Governace should be provisioned with public did and registered for all e2e tests
@pytest.fixture(autouse=True, scope="session")
async def governance_public_did(governance_acapy_client: AcaPyClient) -> str:
    try:
        response = await get_public_did(governance_acapy_client)
    except CloudApiException:
        response = await create_public_did(governance_acapy_client, set_public=True)

    did = response.did

    gov_id = f"test-governance-id-{random_string(3)}"
    if not await actor_by_id(gov_id):
        await register_actor(
            Actor(
                id=gov_id,
                name=f"test-governance-actor-{random_string(3)}",
                roles=["issuer", "verifier"],
                did=f"did:sov:{did}",
            )
        )

    yield did

    await remove_actor_by_id(gov_id)
