import pytest
from assertpy import assert_that

from app.event_handling.sse_listener import SseListener
from app.models.tenants import CreateTenantResponse
from app.routes.definitions import CredentialSchema
from app.routes.issuer import router as issuer_router
from app.routes.oob import router as oob_router
from app.tests.util.ecosystem_connections import FaberAliceConnect
from app.tests.util.webhooks import check_webhook_state, get_wallet_id_from_async_client
from app.util.credentials import cred_id_no_version
from shared import RichAsyncClient

CREDENTIALS_BASE_PATH = issuer_router.prefix
OOB_BASE_PATH = oob_router.prefix


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
        "indy_credential_detail": {
            "credential_definition_id": credential_definition_id,
            "attributes": {"speed": "10"},
        },
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
        OOB_BASE_PATH + "/create-invitation",
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
        OOB_BASE_PATH + "/accept-invitation",
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
        "protocol_version": "v2",
        "connection_id": faber_and_alice_connection.faber_connection_id,
        "indy_credential_detail": {
            "credential_definition_id": credential_definition_id,
            "attributes": {"speed": "10"},
        },
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


@pytest.mark.anyio
async def test_create_offer(
    faber_client: RichAsyncClient,
    schema_definition: CredentialSchema,
    credential_definition_id: str,
):
    credential = {
        "protocol_version": "v2",
        "indy_credential_detail": {
            "credential_definition_id": credential_definition_id,
            "attributes": {"speed": "10"},
        },
    }

    response = await faber_client.post(
        CREDENTIALS_BASE_PATH + "/create-offer",
        json=credential,
    )

    data = response.json()
    assert_that(data).contains("credential_id")
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


@pytest.mark.anyio
async def test_send_credential_request(
    alice_member_client: RichAsyncClient,
    faber_client: RichAsyncClient,
    faber_and_alice_connection: FaberAliceConnect,
    credential_definition_id: str,
):
    credential = {
        "protocol_version": "v2",
        "connection_id": faber_and_alice_connection.faber_connection_id,
        "indy_credential_detail": {
            "credential_definition_id": credential_definition_id,
            "attributes": {"speed": "10"},
        },
    }

    response = await faber_client.post(
        CREDENTIALS_BASE_PATH,
        json=credential,
    )
    credential_exchange = response.json()
    assert credential_exchange["protocol_version"] == "v2"

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

    credential_id = (response.json())[0]["credential_id"]

    assert await check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "offer-received"},
        topic="credentials",
    )

    request_response = await alice_member_client.post(
        f"{CREDENTIALS_BASE_PATH}/{credential_id}/request",
    )

    assert request_response.status_code == 200

    assert await check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "request-sent"},
        topic="credentials",
    )

    assert await check_webhook_state(
        client=faber_client,
        filter_map={"state": "request-received"},
        topic="credentials",
    )


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
        "protocol_version": "v2",
        "connection_id": faber_connection_id,
        "indy_credential_detail": {
            "credential_definition_id": credential_definition_id_revocable,
            "attributes": {"speed": "10"},
        },
    }

    alice_credentials_listener = SseListener(
        topic="credentials", wallet_id=alice_tenant.tenant_id
    )

    # create and send credential offer: issuer
    faber_credential_id = (
        await faber_client.post(
            CREDENTIALS_BASE_PATH,
            json=credential,
        )
    ).json()["credential_id"]

    payload = await alice_credentials_listener.wait_for_event(
        field="connection_id",
        field_id=faber_and_alice_connection.alice_connection_id,
        desired_state="offer-received",
    )

    alice_credential_id = payload["credential_id"]

    # send credential request: holder
    response = await alice_member_client.post(
        f"{CREDENTIALS_BASE_PATH}/{alice_credential_id}/request", json={}
    )

    await alice_credentials_listener.wait_for_event(
        field="credential_id",
        field_id=alice_credential_id,
        desired_state="done",
    )

    cred_id = cred_id_no_version(faber_credential_id)

    response = await faber_client.post(
        f"{CREDENTIALS_BASE_PATH}/revoke",
        json={
            "credential_definition_id": credential_definition_id_revocable,
            "credential_exchange_id": cred_id,
        },
    )

    assert response.status_code == 204
