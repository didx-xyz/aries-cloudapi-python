from typing import Any
import pytest
from aries_cloudcontroller import AcaPyClient
from httpx import AsyncClient
from app.dependencies import acapy_auth, acapy_auth_verified
from app.generic.definitions import (
    CreateCredentialDefinition,
    CreateSchema,
    CredentialSchema,
    create_schema,
    create_credential_definition,
)
from app.tests.util.ecosystem_personas import FaberAliceConnect
from app.tests.util.ledger import create_public_did, has_public_did
from app.tests.util.webhooks import check_webhook_state
from app.generic.issuer.issuer import router

from app.tests.util.trust_registry import register_issuer
from app.webhook_listener import start_listener
from shared_models.shared_models import CredentialExchange

BASE_PATH = router.prefix + "/credentials"

# TODO: Move all methods here to member_personans as this is specific for the bob-alice interaction
# OR abstract the persona specific parts out of it


@pytest.fixture(scope="module")
async def schema_definition(governance_acapy_client: AcaPyClient) -> CredentialSchema:
    definition = CreateSchema(
        name="test_schema", version="0.3", attribute_names=["speed"]
    )

    if not await has_public_did(governance_acapy_client):
        await create_public_did(governance_acapy_client, set_public=True)

    schema_definition_result = await create_schema(definition, governance_acapy_client)

    return schema_definition_result


@pytest.fixture(scope="module")
async def credential_definition_id(
    schema_definition: CredentialSchema,
    faber_client: AsyncClient,
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


@pytest.fixture(scope="module")
async def credential_exchange_id(
    faber_client: AsyncClient,
    credential_definition_id: str,
    faber_and_alice_connection: FaberAliceConnect,
    alice_member_client: AsyncClient,
):
    """this fixture produces the CRED_X_ID but if the test that produces the CRED_X_ID has already run
    then this fixture just returns it..."""
    credential = {
        "protocol_version": "v1",
        "connection_id": faber_and_alice_connection["faber_connection_id"],
        "credential_definition_id": credential_definition_id,
        "attributes": {"speed": "average"},
    }

    response = await faber_client.post(
        BASE_PATH,
        json=credential,
    )
    response.raise_for_status()
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
        BASE_PATH,
        params={"connection_id": faber_and_alice_connection["alice_connection_id"]},
    )
    response.raise_for_status()
    records = response.json()
    assert len(records) > 0

    return credential_exchange_id


@pytest.fixture(scope="module")
async def issue_credential_to_alice(
    faber_client: AsyncClient,
    credential_definition_id: str,
    faber_and_alice_connection: FaberAliceConnect,
    alice_member_client: AsyncClient,
    alice_tenant: Any,
) -> CredentialExchange:
    credential = {
        "protocol_version": "v1",
        "connection_id": faber_and_alice_connection["faber_connection_id"],
        "credential_definition_id": credential_definition_id,
        "attributes": {"speed": "10"},
    }

    wait_for_event, _ = await start_listener(
        topic="credentials", wallet_id=alice_tenant["tenant_id"]
    )

    # create and send credential offer- issuer
    response = await faber_client.post(
        "/generic/issuer/credentials",
        json=credential,
    )
    credential_exchange = response.json()
    if response.is_error:
        print(credential_exchange)
    response.raise_for_status()

    payload = await wait_for_event(
        filter_map={
            "connection_id": faber_and_alice_connection["alice_connection_id"],
            "state": "offer-received",
        }
    )

    alice_credential_id = payload["credential_id"]
    wait_for_event, _ = await start_listener(
        topic="credentials", wallet_id=alice_tenant["tenant_id"]
    )

    # send credential request - holder
    response = await alice_member_client.post(
        f"/generic/issuer/credentials/{alice_credential_id}/request", json={}
    )

    await wait_for_event(
        filter_map={"credential_id": alice_credential_id, "state": "done"}
    )
    return response.json()
