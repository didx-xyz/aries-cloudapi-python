import pytest
from aries_cloudcontroller import SchemaSendResult
from assertpy import assert_that
from httpx import AsyncClient

from app.tests.util.webhooks import get_hooks_per_topic_per_wallet, check_webhook_state

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
        filter_map={"state": "offer-sent"},
        topic="issue_credential",
    )
    response = await alice_member_client.get(
        BASE_PATH,
        params={"connection_id": bob_and_alice_connection["alice_connection_id"]},
    )
    records = response.json()

    assert check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "offer-received"},
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
    alice_member_client: AsyncClient,
    bob_member_client: AsyncClient,
    bob_and_alice_connection: BobAliceConnect,
    schema_definition: SchemaSendResult,
):
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
    assert credential_exchange["protocol_version"] == "v1"

    assert check_webhook_state(
        client=bob_member_client,
        filter_map={
            "state": "offer-sent",
            "credential_id": credential_exchange["credential_id"],
        },
        topic="issue_credential",
    )

    response = await alice_member_client.get(
        BASE_PATH,
        params={"connection_id": bob_and_alice_connection["alice_connection_id"]},
    )
    assert check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "offer-received"},
        topic="issue_credential",
    )


@pytest.mark.asyncio
async def test_store_credential(
    alice_member_client: AsyncClient,
    bob_member_client: AsyncClient,
    credential_exchange_id: str,
    bob_and_alice_connection: BobAliceConnect,
    schema_definition: SchemaSendResult,
):
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
    assert credential_exchange["protocol_version"] == "v1"

    assert check_webhook_state(
        client=bob_member_client,
        filter_map={
            "state": "offer-sent",
            "credential_id": credential_exchange["credential_id"],
        },
        topic="issue_credential",
    )

    response = await alice_member_client.get(
        BASE_PATH,
        params={"connection_id": bob_and_alice_connection["alice_connection_id"]},
    )
    assert check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "offer-received"},
        topic="issue_credential",
    )

    cred_hooks = get_hooks_per_topic_per_wallet(
        client=alice_member_client, topic="issue_credential"
    )

    cred_hook = [h for h in cred_hooks if h["payload"]["state"] == "offer-received"][0]
    credential_id = cred_hook["payload"]["credential_id"]

    response = await alice_member_client.post(f"{BASE_PATH}/{credential_id}/request")

    assert check_webhook_state(
        client=bob_member_client,
        filter_map={"state": "request-received"},
        topic="issue_credential",
    )

    response = await alice_member_client.post(f"{BASE_PATH}/{credential_id}/store")

    assert check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "credential-received"},
        topic="issue_credential",
    )
