import pytest
from aries_cloudcontroller import AcaPyClient
from httpx import AsyncClient
from app.generic.definitions import (
    CreateCredentialDefinition,
    CreateSchema,
    CredentialSchema,
    create_schema,
    create_credential_definition,
)
from app.tests.util.ledger import create_public_did
from app.tests.util.webhooks import check_webhook_state
from app.generic.issuer.issuer import router

from app.tests.util.trust_registry import register_issuer
from app.tests.util.event_loop import event_loop
from app.tests.util.member_personas import (
    BobAliceConnect,
    alice_member_client,
    bob_acapy_client,
    bob_and_alice_connection,
    bob_and_alice_public_did,
    bob_member_client,
)

BASE_PATH = router.prefix + "/credentials"

# TODO: Move all methods here to member_personans as this is specific for the bob-alice interaction
# OR abstract the persona specific parts out of it


@pytest.fixture(scope="module")
async def schema_definition(yoma_acapy_client: AcaPyClient) -> CredentialSchema:
    definition = CreateSchema(
        name="test_schema", version="0.3", attribute_names=["speed"]
    )

    await create_public_did(yoma_acapy_client)

    schema_definition_result = await create_schema(definition, yoma_acapy_client)

    return schema_definition_result


@pytest.fixture(scope="module")
async def credential_definition_id(
    schema_definition: CredentialSchema,
    faber_client: AsyncClient,
    faber_acapy_client: AcaPyClient,
) -> str:
    await register_issuer(faber_client, schema_definition.id)

    definition = CreateCredentialDefinition(tag="tag", schema_id=schema_definition.id)
    result = await create_credential_definition(definition, faber_acapy_client)

    return result.id


@pytest.fixture(scope="module")
async def credential_exchange_id(
    bob_member_client: AsyncClient,
    bob_and_alice_connection: BobAliceConnect,
    schema_definition: CredentialSchema,
    credential_definition_id: str,
    alice_member_client: AsyncClient,
):
    """this fixture produces the CRED_X_ID but if the test that produces the CRED_X_ID has already run
    then this fixture just returns it..."""
    credential = {
        "protocol_version": "v1",
        "connection_id": bob_and_alice_connection["bob_connection_id"],
        "credential_definition_id": credential_definition_id,
        "attributes": {"speed": "average"},
    }

    response = await bob_member_client.post(
        BASE_PATH,
        json=credential,
    )
    credential_exchange = response.json()
    credential_exchange_id = credential_exchange["credential_id"]
    assert credential_exchange["protocol_version"] == "v1"

    assert check_webhook_state(
        client=bob_member_client,
        filter_map={
            "state": "offer-sent",
            "credential_id": credential_exchange["credential_id"],
        },
        topic="credentials",
    )

    response = await alice_member_client.get(
        BASE_PATH,
        params={"connection_id": bob_and_alice_connection["alice_connection_id"]},
    )
    records = response.json()
    assert len(records) > 0

    return credential_exchange_id
