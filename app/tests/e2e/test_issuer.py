import pytest
from assertpy import assert_that
from httpx import AsyncClient
from app.generic.definitions import CredentialSchema
from app.tests.util.ecosystem_personas import FaberAliceConnect
from app.tests.util.webhooks import get_hooks_per_topic_per_wallet, check_webhook_state

# This import are important for tests to run!

from app.tests.e2e.test_fixtures import BASE_PATH
from app.tests.e2e.test_fixtures import *  # NOQA


@pytest.mark.asyncio
async def test_send_credential_oob_v1(
    faber_client: AsyncClient,
    schema_definition: CredentialSchema,
    credential_definition_id: str,
    faber_and_alice_connection: FaberAliceConnect,
    alice_member_client: AsyncClient,
):
    credential = {
        "protocol_version": "v1",
        "credential_definition_id": credential_definition_id,
        "attributes": {"speed": "10"},
    }

    response = await alice_member_client.get(
        BASE_PATH,
        params={"connection_id": faber_and_alice_connection["alice_connection_id"]},
    )
    records = response.json()

    # nothing currently in alice's records
    assert len(records) == 0

    response = await faber_client.post(
        BASE_PATH + "/create-offer",
        json=credential,
    )
    response.raise_for_status()

    data = response.json()
    assert_that(data).contains("credential_id")
    assert_that(data).has_state("offer-sent")
    assert_that(data).has_protocol_version("v1")
    assert_that(data).has_attributes({"speed": "10"})
    assert_that(data).has_schema_id(schema_definition.id)

    invitation_response = await faber_client.post(
        "/generic/oob/create-invitation",
        json={
            "create_connection": False,
            "use_public_did": False,
            "attachments": [
                {"id": data["credential_id"][3:], "type": "credential-offer"}
            ],
        },
    )
    assert_that(invitation_response.status_code).is_equal_to(200)

    invitation = (invitation_response.json())["invitation"]
    invitation["id"] = invitation.pop("@id")
    invitation["type"] = invitation.pop("@type")
    accept_response = await alice_member_client.post(
        "/generic/oob/accept-invitation",
        json={"invitation": invitation},
    )
    accept_response.raise_for_status()

    oob_record = accept_response.json()

    assert_that(accept_response.status_code).is_equal_to(200)
    assert_that(oob_record).contains("created_at", "oob_id", "invitation")
    assert check_webhook_state(
        client=alice_member_client,
        filter_map={
            "state": "offer-received",
            "credential_definition_id": credential_definition_id,
        },
        topic="credentials",
    )


@pytest.mark.asyncio
async def test_send_credential_oob_v2(
    faber_client: AsyncClient,
    schema_definition: CredentialSchema,
    credential_definition_id: str,
    alice_member_client: AsyncClient,
):
    credential = {
        "protocol_version": "v2",
        "credential_definition_id": credential_definition_id,
        "attributes": {"speed": "10"},
    }

    response = await faber_client.post(
        BASE_PATH + "/create-offer",
        json=credential,
    )
    response.raise_for_status()

    data = response.json()
    assert_that(data).contains("credential_id")
    assert_that(data).has_state("offer-sent")
    assert_that(data).has_protocol_version("v2")
    assert_that(data).has_attributes({"speed": "10"})
    assert_that(data).has_schema_id(schema_definition.id)

    invitation_response = await faber_client.post(
        "/generic/oob/create-invitation",
        json={
            "create_connection": False,
            "use_public_did": False,
            "attachments": [
                {"id": data["credential_id"][3:], "type": "credential-offer"}
            ],
        },
    )
    assert_that(invitation_response.status_code).is_equal_to(200)

    invitation = (invitation_response.json())["invitation"]
    invitation["id"] = invitation.pop("@id")
    invitation["type"] = invitation.pop("@type")
    accept_response = await alice_member_client.post(
        "/generic/oob/accept-invitation",
        json={"invitation": invitation},
    )
    accept_response.raise_for_status()

    oob_record = accept_response.json()

    assert_that(accept_response.status_code).is_equal_to(200)
    assert_that(oob_record).contains("created_at", "oob_id", "invitation")
    assert check_webhook_state(
        client=alice_member_client,
        filter_map={
            "state": "offer-received",
            "credential_definition_id": credential_definition_id,
        },
        topic="credentials",
    )


@pytest.mark.asyncio
async def test_send_credential(
    faber_client: AsyncClient,
    schema_definition: CredentialSchema,
    credential_definition_id: str,
    faber_and_alice_connection: FaberAliceConnect,
    alice_member_client: AsyncClient,
):
    credential = {
        "protocol_version": "v1",
        "connection_id": faber_and_alice_connection["faber_connection_id"],
        "credential_definition_id": credential_definition_id,
        "attributes": {"speed": "10"},
    }

    response = await alice_member_client.get(
        BASE_PATH,
        params={"connection_id": faber_and_alice_connection["alice_connection_id"]},
    )
    records = response.json()

    # nothing currently in alice's records
    assert len(records) == 0

    response = await faber_client.post(
        BASE_PATH,
        json=credential,
    )
    response.raise_for_status()

    data = response.json()
    assert_that(data).contains("credential_id")
    assert_that(data).has_state("offer-sent")
    assert_that(data).has_protocol_version("v1")
    assert_that(data).has_attributes({"speed": "10"})
    assert_that(data).has_schema_id(schema_definition.id)

    credential["protocol_version"] = "v2"
    response = await faber_client.post(
        BASE_PATH,
        json=credential,
    )
    response.raise_for_status()

    data = response.json()
    assert_that(data).has_state("offer-sent")
    assert_that(data).has_protocol_version("v2")
    assert_that(data).has_attributes({"speed": "10"})
    assert_that(data).has_schema_id(schema_definition.id)

    assert check_webhook_state(
        client=faber_client,
        filter_map={
            "state": "offer-sent",
            "credential_id": data["credential_id"],
        },
        topic="credentials",
    )
    response = await alice_member_client.get(
        BASE_PATH,
        params={"connection_id": faber_and_alice_connection["alice_connection_id"]},
    )
    records = response.json()

    assert check_webhook_state(
        client=alice_member_client,
        filter_map={
            "state": "offer-received",
            "credential_id": records[-1]["credential_id"],
        },
        topic="credentials",
    )
    assert len(records) == 2

    # Expect one v1 record, one v2 record
    assert_that(records).extracting("protocol_version").contains("v1", "v2")


@pytest.mark.asyncio
async def test_create_offer(
    faber_client: AsyncClient,
    schema_definition: CredentialSchema,
    credential_definition_id: str,
):
    credential = {
        "protocol_version": "v1",
        "credential_definition_id": credential_definition_id,
        "attributes": {"speed": "10"},
    }

    response = await faber_client.post(
        BASE_PATH + "/create-offer",
        json=credential,
    )
    response.raise_for_status()

    data = response.json()
    assert_that(data).contains("credential_id")
    assert_that(data).has_state("offer-sent")
    assert_that(data).has_protocol_version("v1")
    assert_that(data).has_attributes({"speed": "10"})
    assert_that(data).has_schema_id(schema_definition.id)

    credential["protocol_version"] = "v2"
    response = await faber_client.post(
        BASE_PATH + "/create-offer",
        json=credential,
    )
    response.raise_for_status()

    data = response.json()
    assert_that(data).has_state("offer-sent")
    assert_that(data).has_protocol_version("v2")
    assert_that(data).has_attributes({"speed": "10"})
    assert_that(data).has_schema_id(schema_definition.id)

    assert check_webhook_state(
        client=faber_client,
        filter_map={
            "state": "offer-sent",
            "credential_id": data["credential_id"],
        },
        topic="credentials",
    )
    response = await faber_client.get(
        BASE_PATH,
    )
    records = response.json()

    assert check_webhook_state(
        client=faber_client,
        filter_map={
            "state": "offer-sent",
            "credential_id": records[-1]["credential_id"],
        },
        topic="credentials",
    )
    # Two from this and two from previous test potentially. Depending on order.
    # So let's do >= 2 instead of == 2 or == 4
    assert len(records) >= 2

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
    faber_client: AsyncClient,
    faber_and_alice_connection: FaberAliceConnect,
    credential_definition_id: str,
):
    credential = {
        "protocol_version": "v1",
        "credential_definition_id": credential_definition_id,
        "connection_id": faber_and_alice_connection["faber_connection_id"],
        "attributes": {"speed": "10"},
    }

    response = await faber_client.post(
        BASE_PATH,
        json=credential,
    )
    credential_exchange = response.json()
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
    assert check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "offer-received"},
        topic="credentials",
    )


@pytest.mark.asyncio
async def test_store_credential(
    alice_member_client: AsyncClient,
    faber_client: AsyncClient,
    credential_definition_id: str,
    faber_and_alice_connection: FaberAliceConnect,
):
    credential = {
        "protocol_version": "v1",
        "credential_definition_id": credential_definition_id,
        "connection_id": faber_and_alice_connection["faber_connection_id"],
        "attributes": {"speed": "10"},
    }

    response = await faber_client.post(
        BASE_PATH,
        json=credential,
    )
    credential_exchange = response.json()
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
    assert check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "offer-received"},
        topic="credentials",
    )

    cred_hooks = get_hooks_per_topic_per_wallet(
        client=alice_member_client, topic="credentials"
    )

    cred_hook = [h for h in cred_hooks if h["payload"]["state"] == "offer-received"][0]
    credential_id = cred_hook["payload"]["credential_id"]

    # alice send request for that credential
    response = await alice_member_client.post(f"{BASE_PATH}/{credential_id}/request")
    response.raise_for_status()

    # Bob check he received the request; Credential is send because of using
    # 'automating the entire flow' send credential earlier.
    # See also: app/generic/issuer/issuer.py::send_credential
    assert check_webhook_state(
        client=faber_client,
        filter_map={"state": "request-received"},
        topic="credentials",
    )

    # Check alice has received the credential
    assert check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "credential-received"},
        topic="credentials",
    )

    # Alice stores credential
    response = await alice_member_client.post(f"{BASE_PATH}/{credential_id}/store")

    # Check alice has received the credential
    assert check_webhook_state(
        client=alice_member_client, filter_map={"state": "done"}, topic="credentials"
    )
