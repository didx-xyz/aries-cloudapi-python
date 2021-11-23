import time
from random import random
from typing import Any, Dict

import pytest
from assertpy.assertpy import assert_that
from httpx import AsyncClient

from app.facades.trust_registry import (
    Actor,
    actor_by_did,
    register_actor,
    register_schema,
    registry_has_schema,
)
from app.tests.e2e.test_fixtures import BASE_PATH
from app.tests.e2e.test_fixtures import *  # NOQA


# need this to handle the async with the mock
async def get(response):
    return response


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


@pytest.mark.asyncio
async def test_send_credential(
    async_client_bob_module_scope: AsyncClient,
    schema_definition: Dict[str, Any],
    bob_connection_id: str,
    alice_connection_id: str,
    async_client_alice_module_scope: AsyncClient,
):
    credential = {
        "protocol_version": "v1",
        "connection_id": bob_connection_id,
        "schema_id": schema_definition["schema_id"],
        "attributes": {"speed": "average"},
    }

    await register_issuer(async_client_bob_module_scope, schema_definition["schema_id"])

    response = await async_client_alice_module_scope.get(
        BASE_PATH, params={"connection_id": alice_connection_id}
    )
    records = response.json()

    # nothing currently in alice's records
    assert len(records) == 0

    response = await async_client_bob_module_scope.post(
        BASE_PATH,
        json=credential,
    )

    credential["protocol_version"] = "v2"
    response = await async_client_bob_module_scope.post(
        BASE_PATH,
        json=credential,
    )

    time.sleep(5)
    response = await async_client_alice_module_scope.get(
        BASE_PATH, params={"connection_id": alice_connection_id}
    )
    records = response.json()

    assert len(records) == 2

    # Expect one v1 record, one v2 record
    assert_that(records).extracting("protocol_version").contains("v1", "v2")


@pytest.mark.asyncio
async def test_get_records(async_client_alice_module_scope: AsyncClient):
    records = (await async_client_alice_module_scope.get(BASE_PATH)).json()
    assert records
    assert len(records) >= 1


@pytest.mark.asyncio
async def test_send_credential_request(
    async_client_bob_module_scope: AsyncClient, credential_exchange_id: str
):
    time.sleep(10)
    response = await async_client_bob_module_scope.post(
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
    async_client_bob_module_scope: AsyncClient, credential_exchange_id: str
):
    # TODO check for the correct response when state is credential_received
    # We can't complete this with auto accept enabled
    time.sleep(5)
    response = await async_client_bob_module_scope.post(
        f"{BASE_PATH}/{credential_exchange_id}/store"
    )

    result = response.json()

    print(result)

    assert result["error_message"]
    assert ("Credential exchange" and "state (must be credential_received).") in result[
        "error_message"
    ]
    assert response.status_code == 400
