import pytest
from aries_cloudcontroller import AcaPyClient

# flake8: noqa
# pylint: disable=unused-import
from app.exceptions import CloudApiException
from app.services.acapy_wallet import get_public_did
from app.services.trust_registry.actors import (
    fetch_actor_by_id,
    register_actor,
    remove_actor_by_id,
)
from app.tests.util.credentials import (
    issue_alice_creds_and_revoke_published,
    issue_alice_creds_and_revoke_unpublished,
    issue_credential_to_alice,
    meld_co_issue_credential_to_alice,
)
from app.tests.util.definitions import (
    credential_definition_id,
    credential_definition_id_revocable,
    meld_co_credential_definition_id,
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
