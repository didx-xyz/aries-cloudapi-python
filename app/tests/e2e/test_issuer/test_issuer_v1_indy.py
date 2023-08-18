import pytest
from aries_cloudcontroller import AcaPyClient
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
async def test_send_credential_oob_v1(
    faber_client: RichAsyncClient,
    schema_definition: CredentialSchema,
    credential_definition_id: str,
    faber_and_alice_connection: FaberAliceConnect,
    alice_member_client: RichAsyncClient,
):
    credential = {
        "protocol_version": "v1",
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

    accept_response = await alice_member_client.post(
        OOB_BASE_PATH + "/accept-invitation",
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
    assert_that(data).has_protocol_version("v1")
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
        "protocol_version": "v1",
        "indy_credential_detail": {
            "credential_definition_id": credential_definition_id,
            "attributes": {"speed": "10"},
        },
    }

