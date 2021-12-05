import asyncio
import time
from random import random
from typing import Any

import pytest
from aries_cloudcontroller import AcaPyClient
from aries_cloudcontroller.model.schema_send_result import SchemaSendResult
from assertpy.assertpy import assert_that
from httpx import AsyncClient

import app.facades.acapy_ledger as acapy_ledger_facade
from app.admin.governance.schemas import SchemaDefinition, create_schema
from app.facades.trust_registry import (
    Actor,
    actor_by_did,
    register_actor,
    register_schema,
    registry_has_schema,
)
from app.generic.issuer.issuer import router
from app.tests.util.string import get_random_string

# This import are important for tests to run!
from app.tests.util.member_personas import (
    alice_member_client,
    bob_member_client,
    bob_and_alice_connection,
    bob_and_alice_public_did,
    BobAliceConnect,
)
from app.tests.util.event_loop import event_loop
from app.tests.util.client_fixtures import yoma_acapy_client

BASE_PATH = router.prefix + "/credentials"


async def register_issuer(client: AsyncClient, schema_id: str):
    pub_did_res = await client.get("/wallet/fetch-current-did")
    pub_did = pub_did_res.json()["result"]["did"]

    if not await registry_has_schema(schema_id=schema_id):
        await register_schema(schema_id)

    if not await actor_by_did(f"did:sov:{pub_did}"):
        rand = random()
        await register_actor(
            Actor(
                id=f"test-actor-{rand}",
                name=f"Test Actor-{rand}",
                roles=["issuer", "verifier"],
                did=f"did:sov:{pub_did}",
                didcomm_invitation=None,
            )
        )


@pytest.yield_fixture(scope="module")
def event_loop(request: Any):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def schema_definition(
    yoma_acapy_client: AcaPyClient, bob_and_alice_public_did: None
) -> SchemaSendResult:
    definition = SchemaDefinition(
        name="test_schema", version="0.3", attributes=["speed"]
    )

    await acapy_ledger_facade.create_pub_did(yoma_acapy_client)

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

    time.sleep(5)
    response = await alice_member_client.get(
        BASE_PATH,
        params={"connection_id": bob_and_alice_connection["alice_connection_id"]},
    )
    records = response.json()
    assert len(records) > 0

    return credential_exchange_id


@pytest.mark.asyncio
async def test_send_credential(
    bob_member_client: AsyncClient,
    schema_definition: SchemaSendResult,
    bob_and_alice_connection: BobAliceConnect,
    alice_member_client: AsyncClient,
):
    credential = {
        "protocol_version": "v1",
        "connection_id": bob_and_alice_connection["bob_connection_id"],
        "schema_id": schema_definition.schema_id,
        "attributes": {"speed": "average"},
    }

    await register_issuer(bob_member_client, schema_definition.schema_id)

    response = await alice_member_client.get(
        BASE_PATH,
        params={"connection_id": bob_and_alice_connection["alice_connection_id"]},
    )
    records = response.json()

    # nothing currently in alice's records
    assert len(records) == 0

    response = await bob_member_client.post(
        BASE_PATH,
        json=credential,
    )

    credential["protocol_version"] = "v2"
    response = await bob_member_client.post(
        BASE_PATH,
        json=credential,
    )

    time.sleep(5)
    response = await alice_member_client.get(
        BASE_PATH,
        params={"connection_id": bob_and_alice_connection["alice_connection_id"]},
    )
    records = response.json()

    assert len(records) == 2

    # Expect one v1 record, one v2 record
    assert_that(records).extracting("protocol_version").contains("v1", "v2")


@pytest.mark.asyncio
async def test_get_records(alice_member_client: AsyncClient):
    records = (await alice_member_client.get(BASE_PATH)).json()
    assert records
    assert len(records) >= 1


@pytest.mark.asyncio
async def test_send_credential_request(
    bob_member_client: AsyncClient, credential_exchange_id: str
):
    time.sleep(10)
    response = await bob_member_client.post(
        f"{BASE_PATH}/{credential_exchange_id}/request"
    )

    # This returns an error - the correct one because the credential is in state received.
    # For this to return another response we'd have to have state offer_received
    result = response.json()

    assert result["error_message"]
    assert "Credential exchange" in result["error_message"]
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_store_credential(
    bob_member_client: AsyncClient, credential_exchange_id: str
):
    # TODO check for the correct response when state is credential_received
    # We can't complete this with auto accept enabled
    time.sleep(5)
    response = await bob_member_client.post(
        f"{BASE_PATH}/{credential_exchange_id}/store"
    )

    result = response.json()

    print(result)

    assert result["error_message"]
    assert ("Credential exchange" and "state (must be credential_received).") in result[
        "error_message"
    ]
    assert response.status_code == 400
