import pytest
from assertpy import assert_that

from app.exceptions.cloud_api_error import CloudApiException
from app.tests.util.ecosystem_connections import BobAliceConnect
from app.tests.util.webhooks import check_webhook_state
from shared import RichAsyncClient


@pytest.mark.anyio
async def test_create_invitation(
    bob_member_client: RichAsyncClient,
):
    response = await bob_member_client.post("/generic/connections/create-invitation")
    invitation = response.json()

    assert_that(invitation["connection_id"]).is_not_empty()
    assert_that(invitation["invitation"]).is_instance_of(dict).contains(
        "@id", "@type", "recipientKeys", "serviceEndpoint"
    )
    assert_that(invitation["invitation_url"]).matches(r"^https?://")


@pytest.mark.anyio
async def test_accept_invitation(
    bob_member_client: RichAsyncClient,
    alice_member_client: RichAsyncClient,
):
    invitation_response = await bob_member_client.post(
        "/generic/connections/create-invitation"
    )
    invitation = invitation_response.json()

    accept_response = await alice_member_client.post(
        "/generic/connections/accept-invitation",
        json={"invitation": invitation["invitation"]},
    )
    connection_record = accept_response.json()

    assert await check_webhook_state(
        client=alice_member_client,
        topic="connections",
        filter_map={
            "state": "completed",
            "connection_id": connection_record["connection_id"],
        },
    )

    assert_that(connection_record).contains(
        "connection_id", "state", "created_at", "updated_at", "invitation_key"
    )
    assert_that(connection_record).has_state("request-sent")


@pytest.mark.anyio
async def test_get_connections(
    bob_member_client: RichAsyncClient,
    alice_member_client: RichAsyncClient,
    bob_and_alice_connection: BobAliceConnect,
):
    alice_connections = (await alice_member_client.get("/generic/connections")).json()
    bob_connections = (await bob_member_client.get("/generic/connections")).json()

    assert_that(len(alice_connections)).is_greater_than_or_equal_to(1)
    assert_that(len(bob_connections)).is_greater_than_or_equal_to(1)


@pytest.mark.anyio
async def test_get_connection_by_id(
    bob_member_client: RichAsyncClient,
):
    invitation_response = await bob_member_client.post(
        "/generic/connections/create-invitation"
    )
    invitation = invitation_response.json()
    connection_id = invitation["connection_id"]

    connection_response = await bob_member_client.get(
        f"/generic/connections/{connection_id}"
    )
    connection_record = connection_response.json()

    assert_that(connection_response.status_code).is_equal_to(200)
    assert_that(connection_record).contains(
        "connection_id", "state", "created_at", "updated_at", "invitation_key"
    )


@pytest.mark.anyio
async def test_delete_connection(
    bob_member_client: RichAsyncClient,
):
    invitation_response = await bob_member_client.post(
        "/generic/connections/create-invitation"
    )
    invitation = invitation_response.json()
    connection_id = invitation["connection_id"]

    response = await bob_member_client.delete(f"/generic/connections/{connection_id}")
    assert_that(response.status_code).is_equal_to(200)

    with pytest.raises(CloudApiException) as exc:
        response = await bob_member_client.get(f"/generic/connections/{connection_id}")
    assert_that(exc.value.status_code).is_equal_to(404)


@pytest.mark.anyio
async def test_bob_and_alice_connect(
    bob_member_client: RichAsyncClient,
    alice_member_client: RichAsyncClient,
):
    invitation_response = await bob_member_client.post(
        "/generic/connections/create-invitation",
    )
    invitation = invitation_response.json()

    accept_response = await alice_member_client.post(
        "/generic/connections/accept-invitation",
        json={"invitation": invitation["invitation"]},
    )
    connection_record = accept_response.json()

    assert await check_webhook_state(
        client=alice_member_client,
        topic="connections",
        filter_map={
            "state": "completed",
            "connection_id": connection_record["connection_id"],
        },
    )

    alice_connection_id = connection_record["connection_id"]
    bob_connection_id = invitation["connection_id"]

    bob_connection = (
        await bob_member_client.get(f"/generic/connections/{bob_connection_id}")
    ).json()
    alice_connection = (
        await alice_member_client.get(f"/generic/connections/{alice_connection_id}")
    ).json()

    assert "completed" in alice_connection["state"]
    assert "completed" in bob_connection["state"]
