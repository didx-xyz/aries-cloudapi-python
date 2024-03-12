import pytest
from aries_cloudcontroller import AcaPyClient

from app.exceptions import CloudApiException
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
    issue_revocable_credentials_to_alice_and_revoke_published,
    issue_revocable_credentials_to_alice_and_revoke_unpublished,
    meld_co_credential_definition_id,
    meld_co_issue_credential_to_alice,
    schema_definition,
    schema_definition_alt,
)
from app.tests.util.ledger import create_public_did
from shared.log_config import get_logger

logger = get_logger(__name__)


# Governance should be provisioned with public did and registered for all e2e tests
@pytest.fixture(autouse=True, scope="session")
async def governance_public_did(governance_acapy_client: AcaPyClient) -> str:
    logger.info("Configuring public did for governance")

    try:
        response = await get_public_did(governance_acapy_client)
    except CloudApiException as e:
        if e.status_code == 404:
            # Did not found, create and publish
            response = await create_public_did(governance_acapy_client, set_public=True)
        else:
            logger.error(
                "Something went wrong when fetching public did for governance: {}", e
            )
            raise e

    did = response.did

    yield did
