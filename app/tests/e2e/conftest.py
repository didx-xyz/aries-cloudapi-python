import pytest
from aries_cloudcontroller import AcaPyClient

from app.exceptions.cloud_api_error import CloudApiException
from app.models.trust_registry import Actor
from app.services.acapy_wallet import get_public_did
from app.services.trust_registry.actors import (
    fetch_actor_by_id,
    register_actor,
    remove_actor_by_id,
)

# pylint: disable=unused-import
from app.tests.e2e.test_credentials import (  # noqa: F401
    credential_definition_id,
    credential_definition_id_revocable,
    credential_exchange_id,
    issue_credential_to_alice,
    meld_co_credential_definition_id,
    meld_co_issue_credential_to_alice,
    schema_definition,
    schema_definition_alt,
)
from app.tests.util.ledger import create_public_did
from app.util.string import random_string
from shared.log_config import get_logger

logger = get_logger(__name__)


# Governance should be provisioned with public did and registered for all e2e tests
@pytest.fixture(autouse=True, scope="session")
async def governance_public_did(governance_acapy_client: AcaPyClient) -> str:
    logger.info("Configuring public did for governance")

    try:
        response = await get_public_did(governance_acapy_client)
    except CloudApiException:
        response = await create_public_did(governance_acapy_client, set_public=True)

    did = response.did

    gov_id = f"test-governance-id-{random_string(3)}"
    if not await fetch_actor_by_id(gov_id):
        logger.info("Registering actor for governance controller")
        await register_actor(
            Actor(
                id=gov_id,
                name=f"test-governance-actor-{random_string(3)}",
                roles=["issuer", "verifier"],
                did=f"did:sov:{did}",
            )
        )

    yield did

    logger.info("Removing governance actor in test teardown")
    await remove_actor_by_id(gov_id)
    logger.info("Successfully removed governance actor in teardown.")
