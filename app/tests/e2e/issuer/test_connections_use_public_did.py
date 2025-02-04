import pytest
from assertpy import assert_that

from app.models.connections import AcceptInvitation, CreateInvitation
from app.routes.connections import router
from app.tests.util.webhooks import check_webhook_state
from shared import RichAsyncClient


# Apply the marker to all tests in this module
pytestmark = pytest.mark.xdist_group(name="issuer_test_group")

CONNECTIONS_BASE_PATH = router.prefix


@pytest.mark.anyio
async def test_accept_use_public_did(
    faber_client: RichAsyncClient,  # issuer has public did
    meld_co_client: RichAsyncClient,  # also has public did
):
    invite_json = CreateInvitation(use_public_did=True).model_dump()

    response = await faber_client.post(
        f"{CONNECTIONS_BASE_PATH}/create-invitation", json=invite_json
    )
    assert response.status_code == 200

    invitation = response.json()
    assert_that(invitation["connection_id"]).is_not_empty()
    assert_that(invitation["invitation"]).is_instance_of(dict).contains(
        "@id", "@type", "recipientKeys", "serviceEndpoint"
    )
    assert_that(invitation["invitation_url"]).matches(r"^https?://")

    accept_invite_json = AcceptInvitation(
        invitation=invitation["invitation"],
    ).model_dump()

    accept_response = await meld_co_client.post(
        f"{CONNECTIONS_BASE_PATH}/accept-invitation",
        json=accept_invite_json,
    )
    connection_record = accept_response.json()

    assert_that(connection_record).contains(
        "connection_id", "state", "created_at", "updated_at", "invitation_key"
    )
    assert_that(connection_record).has_state("request-sent")

    assert await check_webhook_state(
        client=meld_co_client,
        topic="connections",
        state="completed",
        filter_map={
            "connection_id": connection_record["connection_id"],
        },
    )


@pytest.mark.anyio
async def test_accept_use_public_did_between_issuer_and_holder(
    faber_client: RichAsyncClient,  # issuer has public did
    alice_member_client: RichAsyncClient,  # no public did
):
    invite_json = CreateInvitation(use_public_did=True).model_dump()

    response = await faber_client.post(
        f"{CONNECTIONS_BASE_PATH}/create-invitation", json=invite_json
    )
    assert response.status_code == 200

    invitation = response.json()
    assert_that(invitation["connection_id"]).is_not_empty()
    assert_that(invitation["invitation"]).is_instance_of(dict).contains(
        "@id", "@type", "recipientKeys", "serviceEndpoint"
    )
    assert_that(invitation["invitation_url"]).matches(r"^https?://")

    accept_invite_json = AcceptInvitation(
        invitation=invitation["invitation"]
    ).model_dump()

    accept_response = await alice_member_client.post(
        f"{CONNECTIONS_BASE_PATH}/accept-invitation",
        json=accept_invite_json,
    )
    connection_record = accept_response.json()

    assert_that(connection_record).contains(
        "connection_id", "state", "created_at", "updated_at", "invitation_key"
    )
    assert_that(connection_record).has_state("request-sent")

    assert await check_webhook_state(
        client=alice_member_client,
        topic="connections",
        state="completed",
        filter_map={
            "connection_id": connection_record["connection_id"],
        },
    )
