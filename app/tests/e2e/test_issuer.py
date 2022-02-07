import time

import pytest
from aries_cloudcontroller import SchemaSendResult
from assertpy import assert_that
from httpx import AsyncClient


# This import are important for tests to run!
from app.tests.util.member_personas import (
    BobAliceConnect,
)
from app.tests.util.event_loop import event_loop

from app.tests.e2e.test_fixtures import BASE_PATH
from app.tests.e2e.test_fixtures import *  # NOQA


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
    response.raise_for_status()

    data = response.json()
    assert_that(data).contains("credential_id")
    assert_that(data).has_state("offer-sent")
    assert_that(data).has_protocol_version("v1")
    assert_that(data).has_attributes({"speed": "average"})
    assert_that(data).has_schema_id(schema_definition.schema_id)

    credential["protocol_version"] = "v2"
    response = await bob_member_client.post(
        BASE_PATH,
        json=credential,
    )
    response.raise_for_status()

    data = response.json()
    assert_that(data).has_state("offer-sent")
    assert_that(data).has_protocol_version("v2")
    assert_that(data).has_attributes({"speed": "average"})
    assert_that(data).has_schema_id(schema_definition.schema_id)

    assert check_webhook_state(
        client=bob_member_client,
        desired_state={"state": "offer-sent"},
        topic="issue_credential",
    )
    response = await alice_member_client.get(
        BASE_PATH,
        params={"connection_id": bob_and_alice_connection["alice_connection_id"]},
    )
    records = response.json()

    assert check_webhook_state(
        client=alice_member_client,
        desired_state={"state": "offer-received"},
        topic="issue_credential",
    )
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
    assert check_webhook_state(
        client=bob_member_client,
        desired_state={"state": "offer-sent"},
        topic="issue_credential",
    )
    response = await bob_member_client.post(
        f"{BASE_PATH}/{credential_exchange_id}/request"
    )

    # This returns an error - the correct one because the credential is in state received.
    # For this to return another response we'd have to have state offer_received
    result = response.json()

    assert response.status_code == 400
    assert_that(result).contains("detail")
    assert "in offer_sent state (must be offer_received)" in result["detail"]


@pytest.mark.asyncio
async def test_store_credential(
    bob_member_client: AsyncClient, credential_exchange_id: str
):
    # TODO check for the correct response when state is credential_received
    # We can't complete this with auto accept enabled
    assert check_webhook_state(
        client=bob_member_client,
        desired_state={"state": "offer-sent"},
        topic="issue_credential",
    )
    response = await bob_member_client.post(
        f"{BASE_PATH}/{credential_exchange_id}/store"
    )

    result = response.json()

    assert response.status_code == 400
    assert_that(result).contains("detail")
    assert "state (must be credential_received)." in result["detail"]
