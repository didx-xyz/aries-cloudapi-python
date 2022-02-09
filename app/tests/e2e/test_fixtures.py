import time
import pytest
from aries_cloudcontroller import AcaPyClient, SchemaSendResult
from httpx import AsyncClient
from app.admin.governance.schemas import SchemaDefinition, create_schema
from app.tests.util.ledger import create_public_did
from app.tests.util.webhooks import FilterMap, check_webhook_state
from app.generic.issuer.issuer import router

from app.tests.util.trust_registry import register_issuer
from app.tests.util.event_loop import event_loop
from app.tests.util.member_personas import (
    BobAliceConnect,
    alice_member_client,
    bob_and_alice_connection,
    bob_and_alice_public_did,
    bob_member_client,
)
from app.tests.util.string import get_random_string

BASE_PATH = router.prefix + "/credentials"

# TODO: Move all methods here to member_personans as this is specific for the bob-alice interaction
# OR abstract the persona specific parts out of it


@pytest.fixture(scope="module")
async def schema_definition(
    yoma_acapy_client: AcaPyClient, bob_and_alice_public_did: None
) -> SchemaSendResult:
    definition = SchemaDefinition(
        name="test_schema", version="0.3", attributes=["speed"]
    )

    await create_public_did(yoma_acapy_client)

    schema_definition_result = await create_schema(definition, yoma_acapy_client)

    return schema_definition_result


@pytest.fixture(scope="module")
async def credential_definition_id(
    bob_member_client: AsyncClient, schema_definition: SchemaSendResult
) -> str:
    # when
    response = await bob_member_client.post(
        "/admin/governance/credential-definitions",
        json={
            "support_revocation": False,
            "schema_id": schema_definition.schema_id,
            "tag": get_random_string(5),
        },
    )

    if response.status_code != 200:
        raise Exception(f"Error creating credential definition: {response.text}")

    result = response.json()
    return result["credential_definition_id"]


@pytest.fixture(scope="module")
async def credential_exchange_id(
    bob_member_client: AsyncClient,
    bob_and_alice_connection: BobAliceConnect,
    schema_definition: SchemaSendResult,
    alice_member_client: AsyncClient,
):
    """this fixture produces the CRED_X_ID but if the test that produces the CRED_X_ID has already run
    then this fixture just returns it..."""
    credential = {
        "protocol_version": "v1",
        "connection_id": bob_and_alice_connection["bob_connection_id"],
        "schema_id": schema_definition.schema_id,
        "attributes": {"speed": "average"},
    }

    await register_issuer(bob_member_client, schema_definition.schema_id)

    response = await bob_member_client.post(
        BASE_PATH,
        json=credential,
    )
    credential_exchange = response.json()
    credential_exchange_id = credential_exchange["credential_id"]
    assert credential_exchange["protocol_version"] == "v1"

    assert check_webhook_state(
        client=bob_member_client,
        filter_map=FilterMap(
            filter_key="credential_exchange_id",
            filter_value=credential_exchange["credential_id"],
        ),
        desired_state={"state": "offer-sent"},
        topic="issue_credential",
    )

    response = await alice_member_client.get(
        BASE_PATH,
        params={"connection_id": bob_and_alice_connection["alice_connection_id"]},
    )
    records = response.json()
    assert len(records) > 0

    return credential_exchange_id
