import pytest

from app.dependencies.auth import AcaPyAuthVerified, acapy_auth, acapy_auth_verified
from app.event_handling.sse_listener import SseListener
from app.models.tenants import CreateTenantResponse
from app.routes.definitions import (
    CreateCredentialDefinition,
    CreateSchema,
    CredentialSchema,
    create_credential_definition,
    create_schema,
)
from app.routes.issuer import router
from app.tests.util.ecosystem_connections import FaberAliceConnect
from app.tests.util.trust_registry import register_issuer
from app.tests.util.webhooks import check_webhook_state
from app.util.string import random_version
from shared import RichAsyncClient
from shared.models.topics import CredentialExchange

CREDENTIALS_BASE_PATH = router.prefix + "/credentials"


@pytest.fixture(scope="function")
async def schema_definition(
    mock_governance_auth: AcaPyAuthVerified,
) -> CredentialSchema:
    definition = CreateSchema(
        name="test_schema", version=random_version(), attribute_names=["speed"]
    )

    schema_definition_result = await create_schema(definition, mock_governance_auth)

    return schema_definition_result


@pytest.fixture(scope="function")
async def schema_definition_alt(
    mock_governance_auth: AcaPyAuthVerified,
) -> CredentialSchema:
    definition = CreateSchema(
        name="test_schema_alt", version=random_version(), attribute_names=["speed"]
    )

    schema_definition_result = await create_schema(definition, mock_governance_auth)

    return schema_definition_result


@pytest.fixture(scope="function")
async def credential_definition_id(
    schema_definition: CredentialSchema,
    faber_client: RichAsyncClient,
) -> str:
    await register_issuer(faber_client, schema_definition.id)

    # Support revocation false here because revocation is tested elsewhere.
    # No revocation is a fair bit faster to run
    definition = CreateCredentialDefinition(
        tag="tag", schema_id=schema_definition.id, support_revocation=False
    )

    auth = acapy_auth_verified(acapy_auth(faber_client.headers["x-api-key"]))
    result = await create_credential_definition(definition, auth)

    return result.id


@pytest.fixture(scope="function")
async def credential_definition_id_revocable(
    schema_definition_alt: CredentialSchema,
    faber_client: RichAsyncClient,
) -> str:
    await register_issuer(faber_client, schema_definition_alt.id)

    # Support revocation false here because revocation is tested elsewhere.
    # No revocation is a fair bit faster to run
    definition = CreateCredentialDefinition(
        tag="tag", schema_id=schema_definition_alt.id, support_revocation=True
    )

    auth = acapy_auth_verified(acapy_auth(faber_client.headers["x-api-key"]))
    result = await create_credential_definition(definition, auth)

    return result.id


@pytest.fixture(scope="function")
async def credential_exchange_id(
    faber_client: RichAsyncClient,
    credential_definition_id: str,
    faber_and_alice_connection: FaberAliceConnect,
    alice_member_client: RichAsyncClient,
):
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

    assert await check_webhook_state(
        client=faber_client,
        topic="credentials",
        filter_map={
            "state": "offer-sent",
            "credential_id": credential_exchange["credential_id"],
        },
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

    listener = SseListener(topic="credentials", wallet_id=alice_tenant.tenant_id)

    # create and send credential offer- issuer
    await faber_client.post(
        CREDENTIALS_BASE_PATH,
        json=credential,
    )

    payload = await listener.wait_for_event(
        field="connection_id",
        field_id=faber_and_alice_connection.alice_connection_id,
        desired_state="offer-received",
    )

    alice_credential_id = payload["credential_id"]

    # send credential request - holder
    response = await alice_member_client.post(
        f"{CREDENTIALS_BASE_PATH}/{alice_credential_id}/request", json={}
    )

    await listener.wait_for_event(
        field="credential_id", field_id=alice_credential_id, desired_state="done"
    )

    return response.json()
