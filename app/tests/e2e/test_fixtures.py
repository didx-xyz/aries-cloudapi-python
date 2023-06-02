import pytest
from aries_cloudcontroller import AcaPyClient

from app.admin.tenants.models import CreateTenantResponse
from app.dependencies import acapy_auth, acapy_auth_verified
from app.generic.definitions import (
    CreateCredentialDefinition,
    CreateSchema,
    CredentialSchema,
    create_credential_definition,
    create_schema,
)
from app.generic.issuer.issuer import router
from app.listener import Listener
from app.tests.util.ecosystem_connections import FaberAliceConnect
from app.tests.util.string import random_version
from app.tests.util.trust_registry import register_issuer
from app.tests.util.webhooks import check_webhook_state
from shared import RichAsyncClient
from shared.models.topics import CredentialExchange

CREDENTIALS_BASE_PATH = router.prefix + "/credentials"

# TODO: Move all methods here to member_personans as this is specific for the bob-alice interaction
# OR abstract the persona specific parts out of it


@pytest.fixture(scope="session")
async def schema_definition(governance_acapy_client: AcaPyClient) -> CredentialSchema:
    definition = CreateSchema(
        name="test_schema", version=random_version(), attribute_names=["speed"]
    )

    schema_definition_result = await create_schema(definition, governance_acapy_client)

    return schema_definition_result


@pytest.fixture(scope="session")
async def schema_definition_alt(
    governance_acapy_client: AcaPyClient,
) -> CredentialSchema:
    definition = CreateSchema(
        name="test_schema_alt", version=random_version(), attribute_names=["speed"]
    )

    schema_definition_result = await create_schema(definition, governance_acapy_client)

    return schema_definition_result


@pytest.fixture(scope="function")
async def credential_definition_id(
    schema_definition: CredentialSchema,
    faber_client: RichAsyncClient,
    faber_acapy_client: AcaPyClient,
) -> str:
    await register_issuer(faber_client, schema_definition.id)

    # Support revocation false here because revocation is tested elsewhere.
    # No revocation is a fair bit faster to run
    definition = CreateCredentialDefinition(
        tag="tag", schema_id=schema_definition.id, support_revocation=False
    )

    auth = acapy_auth_verified(acapy_auth(faber_client.headers["x-api-key"]))
    result = await create_credential_definition(definition, faber_acapy_client, auth)

    return result.id


@pytest.fixture(scope="function")
async def credential_definition_id_revocable(
    schema_definition_alt: CredentialSchema,
    faber_client: RichAsyncClient,
    faber_acapy_client: AcaPyClient,
) -> str:
    await register_issuer(faber_client, schema_definition_alt.id)

    # Support revocation false here because revocation is tested elsewhere.
    # No revocation is a fair bit faster to run
    definition = CreateCredentialDefinition(
        tag="tag", schema_id=schema_definition_alt.id, support_revocation=True
    )

    auth = acapy_auth_verified(acapy_auth(faber_client.headers["x-api-key"]))
    result = await create_credential_definition(definition, faber_acapy_client, auth)

    return result.id


@pytest.fixture(scope="function")
async def credential_exchange_id(
    faber_client: RichAsyncClient,
    credential_definition_id: str,
    faber_and_alice_connection: FaberAliceConnect,
    alice_member_client: RichAsyncClient,
):
    """this fixture produces the CRED_X_ID but if the test that produces the CRED_X_ID has already run
    then this fixture just returns it..."""
    credential = {
        "protocol_version": "v1",
        "connection_id": faber_and_alice_connection.faber_connection_id,
        "credential_definition_id": credential_definition_id,
        "attributes": {"speed": "average"},
    }

    response = await faber_client.post(
        CREDENTIALS_BASE_PATH,
        json=credential,
    )
    credential_exchange = response.json()
    credential_exchange_id = credential_exchange["credential_id"]
    assert credential_exchange["protocol_version"] == "v1"

    assert check_webhook_state(
        client=faber_client,
        filter_map={
            "state": "offer-sent",
            "credential_id": credential_exchange["credential_id"],
        },
        topic="credentials",
    )

    response = await alice_member_client.get(
        CREDENTIALS_BASE_PATH,
        params={"connection_id": faber_and_alice_connection.alice_connection_id},
    )
    records = response.json()
    assert len(records) > 0

    return credential_exchange_id


@pytest.fixture(scope="function")
async def issue_credential_to_alice(
    faber_client: RichAsyncClient,
    credential_definition_id: str,
    faber_and_alice_connection: FaberAliceConnect,
    alice_member_client: RichAsyncClient,
    alice_tenant: CreateTenantResponse,
) -> CredentialExchange:
    credential = {
        "protocol_version": "v1",
        "connection_id": faber_and_alice_connection.faber_connection_id,
        "credential_definition_id": credential_definition_id,
        "attributes": {"speed": "10"},
    }

    listener = Listener(topic="credentials", wallet_id=alice_tenant.tenant_id)

    # create and send credential offer- issuer
    await faber_client.post(
        "/generic/issuer/credentials",
        json=credential,
    )

    payload = await listener.wait_for_filtered_event(
        filter_map={
            "connection_id": faber_and_alice_connection.alice_connection_id,
            "state": "offer-received",
        }
    )

    alice_credential_id = payload["credential_id"]

    # send credential request - holder
    response = await alice_member_client.post(
        f"/generic/issuer/credentials/{alice_credential_id}/request", json={}
    )

    await listener.wait_for_filtered_event(
        filter_map={"credential_id": alice_credential_id, "state": "done"}
    )
    listener.stop()

    # await alice_member_client.post(f"/generic/issuer/credentials/{alice_credential_id}/store", json={})

    return response.json()
