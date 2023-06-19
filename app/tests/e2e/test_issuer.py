import logging

import pytest
from assertpy import assert_that

from app.admin.tenants.models import CreateTenantResponse
from app.event_handling.sse_listener import SseListener
from app.generic.definitions import CredentialSchema
from app.generic.issuer.facades.acapy_issuer_utils import cred_id_no_version
from app.tests.e2e.test_fixtures import CREDENTIALS_BASE_PATH
from app.tests.util.ecosystem_connections import FaberAliceConnect
from app.tests.util.webhooks import check_webhook_state, get_wallet_id_from_async_client
from shared import CredentialExchange, RichAsyncClient

logger = logging.getLogger(__name__)


@pytest.mark.anyio
async def test_send_credential_oob_v1(
    faber_client: RichAsyncClient,
    schema_definition: CredentialSchema,
    credential_definition_id: str,
    faber_and_alice_connection: FaberAliceConnect,
    alice_member_client: RichAsyncClient,
):
    credential = {
        "protocol_version": "v1",
        "credential_definition_id": credential_definition_id,
        "attributes": {"speed": "10"},
    }

    response = await alice_member_client.get(
        CREDENTIALS_BASE_PATH,
        params={"connection_id": faber_and_alice_connection.alice_connection_id},
    )
    records = response.json()

    # nothing currently in alice's records
    assert len(records) == 0

    response = await faber_client.post(
        CREDENTIALS_BASE_PATH + "/create-offer",
        json=credential,
    )

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

    accept_response = await alice_member_client.post(
        "/generic/oob/accept-invitation",
        json={"invitation": invitation},
    )

    oob_record = accept_response.json()

    assert_that(accept_response.status_code).is_equal_to(200)
    assert_that(oob_record).contains("created_at", "oob_id", "invitation")
    assert await check_webhook_state(
        client=alice_member_client,
        topic="credentials",
        filter_map={
            "state": "offer-received",
            "credential_definition_id": credential_definition_id,
        },
    )


@pytest.mark.anyio
async def test_send_credential_oob_v2(
    faber_client: RichAsyncClient,
    schema_definition: CredentialSchema,
    credential_definition_id: str,
    alice_member_client: RichAsyncClient,
):
    wallet_id = get_wallet_id_from_async_client(alice_member_client)
    alice_credentials_listener = SseListener(topic="credentials", wallet_id=wallet_id)

    credential = {
        "protocol_version": "v2",
        "credential_definition_id": credential_definition_id,
        "attributes": {"speed": "10"},
    }

    create_offer_response = await faber_client.post(
        CREDENTIALS_BASE_PATH + "/create-offer",
        json=credential,
    )

    data = create_offer_response.json()
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

    thread_id = invitation["requests~attach"][0]["data"]["json"]["@id"]

    accept_response = await alice_member_client.post(
        "/generic/oob/accept-invitation",
        json={"invitation": invitation},
    )

    oob_record = accept_response.json()

    assert_that(accept_response.status_code).is_equal_to(200)
    assert_that(oob_record).contains("created_at", "oob_id", "invitation")

    result = await alice_credentials_listener.wait_for_event(
        field="thread_id",
        field_id=thread_id,
        desired_state="offer-received",
    )

    assert result["credential_id"]


@pytest.mark.anyio
async def test_send_credential(
    faber_client: RichAsyncClient,
    schema_definition: CredentialSchema,
    credential_definition_id: str,
    faber_and_alice_connection: FaberAliceConnect,
    alice_member_client: RichAsyncClient,
):
    credential = {
        "protocol_version": "v1",
        "connection_id": faber_and_alice_connection.faber_connection_id,
        "credential_definition_id": credential_definition_id,
        "attributes": {"speed": "10"},
    }

    response = await alice_member_client.get(
        CREDENTIALS_BASE_PATH,
        params={"connection_id": faber_and_alice_connection.alice_connection_id},
    )
    records = response.json()

    # nothing currently in alice's records
    assert len(records) == 0

    response = await faber_client.post(
        CREDENTIALS_BASE_PATH,
        json=credential,
    )

    data = response.json()
    assert_that(data).contains("credential_id")
    assert_that(data).has_state("offer-sent")
    assert_that(data).has_protocol_version("v1")
    assert_that(data).has_attributes({"speed": "10"})
    assert_that(data).has_schema_id(schema_definition.id)

    credential["protocol_version"] = "v2"
    response = await faber_client.post(
        CREDENTIALS_BASE_PATH,
        json=credential,
    )

    data = response.json()
    assert_that(data).has_state("offer-sent")
    assert_that(data).has_protocol_version("v2")
    assert_that(data).has_attributes({"speed": "10"})
    assert_that(data).has_schema_id(schema_definition.id)

    assert await check_webhook_state(
        client=faber_client,
        topic="credentials",
        filter_map={
            "state": "offer-sent",
            "credential_id": data["credential_id"],
        },
    )
    response = await alice_member_client.get(
        CREDENTIALS_BASE_PATH,
        params={"connection_id": faber_and_alice_connection.alice_connection_id},
    )
    records = response.json()

    assert await check_webhook_state(
        client=alice_member_client,
        topic="credentials",
        filter_map={
            "state": "offer-received",
            "credential_id": records[-1]["credential_id"],
        },
    )
    assert len(records) == 2

    # Expect one v1 record, one v2 record
    assert_that(records).extracting("protocol_version").contains("v1", "v2")


@pytest.mark.anyio
async def test_create_offer(
    faber_client: RichAsyncClient,
    schema_definition: CredentialSchema,
    credential_definition_id: str,
):
    credential = {
        "protocol_version": "v1",
        "credential_definition_id": credential_definition_id,
        "attributes": {"speed": "10"},
    }

    response = await faber_client.post(
        CREDENTIALS_BASE_PATH + "/create-offer",
        json=credential,
    )

    data = response.json()
    assert_that(data).contains("credential_id")
    assert_that(data).has_state("offer-sent")
    assert_that(data).has_protocol_version("v1")
    assert_that(data).has_attributes({"speed": "10"})
    assert_that(data).has_schema_id(schema_definition.id)

    credential["protocol_version"] = "v2"
    response = await faber_client.post(
        CREDENTIALS_BASE_PATH + "/create-offer",
        json=credential,
    )

    data = response.json()
    assert_that(data).has_state("offer-sent")
    assert_that(data).has_protocol_version("v2")
    assert_that(data).has_attributes({"speed": "10"})
    assert_that(data).has_schema_id(schema_definition.id)

    assert await check_webhook_state(
        client=faber_client,
        topic="credentials",
        filter_map={
            "state": "offer-sent",
            "credential_id": data["credential_id"],
        },
    )
    response = await faber_client.get(
        CREDENTIALS_BASE_PATH,
    )
    records = response.json()

    assert await check_webhook_state(
        client=faber_client,
        topic="credentials",
        filter_map={
            "state": "offer-sent",
            "credential_id": records[-1]["credential_id"],
        },
    )
    # Two from this and two from previous test potentially. Depending on order.
    # So let's do >= 2 instead of == 2 or == 4
    assert len(records) >= 2

    # Expect one v1 record, one v2 record
    assert_that(records).extracting("protocol_version").contains("v1", "v2")


@pytest.mark.anyio
async def test_send_credential_request(
    alice_member_client: RichAsyncClient,
    faber_client: RichAsyncClient,
    faber_and_alice_connection: FaberAliceConnect,
    credential_definition_id: str,
):
    credential = {
        "protocol_version": "v1",
        "credential_definition_id": credential_definition_id,
        "connection_id": faber_and_alice_connection.faber_connection_id,
        "attributes": {"speed": "10"},
    }

    response = await faber_client.post(
        CREDENTIALS_BASE_PATH,
        json=credential,
    )
    credential_exchange = response.json()
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
    assert await check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "offer-received"},
        topic="credentials",
    )


# Turned off this test because of the parameter below set in
# ../../../environments/governance-multitenant/aca-py-agent.default.env
# ACAPY_AUTO_STORE_CREDENTIAL=true
# @pytest.mark.anyio
# async def test_store_credential(
#     alice_member_client: RichAsyncClient,
#     faber_client: RichAsyncClient,
#     credential_definition_id: str,
#     faber_and_alice_connection: FaberAliceConnect,
# ):
#     sleep(5)
#     credential = {
#         "protocol_version": "v1",
#         "credential_definition_id": credential_definition_id,
#         "connection_id": faber_and_alice_connection["faber_connection_id"],
#         "attributes": {"speed": "10"},
#     }
#
#     response = await faber_client.post(
#         BASE_PATH,
#         json=credential,
#     )
#     credential_exchange = response.json()
#     assert credential_exchange["protocol_version"] == "v1"
#
#     assert check_webhook_state(
#         client=faber_client,
#         filter_map={
#             "state": "offer-sent",
#             "credential_id": credential_exchange["credential_id"],
#         },
#         topic="credentials",
#     )
#
#     response = await alice_member_client.get(
#         BASE_PATH,
#         params={"connection_id": faber_and_alice_connection["alice_connection_id"]},
#     )
#     assert check_webhook_state(
#         client=alice_member_client,
#         filter_map={"state": "offer-received"},
#         topic="credentials",
#         max_duration=240,
#     )
#
#     cred_hooks = get_hooks_per_topic_per_wallet(
#         client=alice_member_client, topic="credentials"
#     )
#
#     cred_hook = [h for h in cred_hooks if h["payload"]["state"] == "offer-received"][-1]
#     credential_id = cred_hook["payload"]["credential_id"]
#
#     # alice send request for that credential
#     response = await alice_member_client.post(f"{BASE_PATH}/{credential_id}/request")
#     response.raise_for_status()
#
#     # Bob check he received the request; Credential is send because of using
#     # 'automating the entire flow' send credential earlier.
#     # See also: app/generic/issuer/issuer.py::send_credential
#     assert check_webhook_state(
#         client=faber_client,
#         filter_map={"state": "request-received"},
#         topic="credentials",
#         max_duration=240,
#     )
#
#     # Check alice has received the credential
#     assert check_webhook_state(
#         client=alice_member_client,
#         filter_map={"state": "offer-received"},
#         topic="credentials",
#         max_duration=240,
#     )
#
#     # Alice stores credential
#     response = await alice_member_client.post(f"{BASE_PATH}/{credential_id}/store")
#
#     # Check alice has received the credential
#     assert check_webhook_state(
#         client=alice_member_client,
#         filter_map={"state": "done"},
#         topic="credentials",
#         max_duration=360,
#     )


@pytest.mark.anyio
async def test_revoke_credential(
    faber_client: RichAsyncClient,
    alice_member_client: RichAsyncClient,
    alice_tenant: CreateTenantResponse,
    credential_definition_id_revocable: str,
    faber_and_alice_connection: FaberAliceConnect,
):
    faber_connection_id = faber_and_alice_connection.faber_connection_id

    credential = {
        "protocol_version": "v1",
        "connection_id": faber_connection_id,
        "credential_definition_id": credential_definition_id_revocable,
        "attributes": {"speed": "10"},
    }

    alice_credentials_listener = SseListener(
        topic="credentials", wallet_id=alice_tenant.tenant_id
    )

    # create and send credential offer- issuer
    await faber_client.post(
        "/generic/issuer/credentials",
        json=credential,
    )

    payload = await alice_credentials_listener.wait_for_event(
        field="connection_id",
        field_id=faber_and_alice_connection.alice_connection_id,
        desired_state="offer-received",
    )

    alice_credential_id = payload["credential_id"]

    # send credential request - holder
    response = await alice_member_client.post(
        f"/generic/issuer/credentials/{alice_credential_id}/request", json={}
    )

    await alice_credentials_listener.wait_for_event(
        field="credential_id",
        field_id=alice_credential_id,
        desired_state="done",
    )

    # Retrieve an issued credential
    records = (await faber_client.get("/generic/issuer/credentials")).json()
    record_as_issuer_for_alice = [
        rec
        for rec in records
        if (
            rec["role"] == "issuer"
            and rec["state"] in ("credential-issued", "done")
            and rec["connection_id"] == faber_connection_id
        )
    ]

    if record_as_issuer_for_alice:
        record_issuer_for_alice: CredentialExchange = record_as_issuer_for_alice[-1]
    else:
        logger.warning(
            "No records matched state: `credential-issued` or `done` with role: `issuer`."
            + f"Looking for connection_id = {faber_connection_id}. List of records retreived: {records}.\n"
        )
        raise Exception("No issued credential retreived.")

    cred_id = cred_id_no_version(record_issuer_for_alice["credential_id"])

    response = await faber_client.post(
        "/generic/issuer/credentials/revoke",
        json={
            "credential_definition_id": credential_definition_id_revocable,
            "credential_exchange_id": cred_id,
        },
    )

    assert response.status_code == 204
