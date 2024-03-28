from typing import Optional

import pytest
from assertpy import assert_that
from fastapi import HTTPException

from app.models.connections import AcceptInvitation, CreateInvitation
from app.routes.connections import router
from app.tests.util.ecosystem_connections import BobAliceConnect
from app.tests.util.webhooks import check_webhook_state
from shared import RichAsyncClient

BASE_PATH = router.prefix


@pytest.mark.anyio
@pytest.mark.parametrize(
    "alias,multi_use,use_public_did",
    [
        (None, None, None),
        ("alias", False, False),
        ("alias", True, False),
        ("alias", False, True),
        ("alias", True, True),
    ],
)
async def test_create_invitation_no_public_did(
    bob_member_client: RichAsyncClient,  # bob has no public did
    alias: Optional[str],
    multi_use: Optional[bool],
    use_public_did: Optional[bool],
):
    invite_json = CreateInvitation(
        alias=alias, multi_use=multi_use, use_public_did=use_public_did
    ).model_dump()

    if use_public_did:
        with pytest.raises(HTTPException) as exc_info:
            # regular holders cannot `use_public_did` as they do not have a public did
            await bob_member_client.post(
                f"{BASE_PATH}/create-invitation", json=invite_json
            )
        assert exc_info.value.status_code == 400
        assert (
            exc_info.value.detail
            == """{"detail":"Cannot create public invitation with no public DID."}"""
        )
    else:
        response = await bob_member_client.post(
            f"{BASE_PATH}/create-invitation", json=invite_json
        )
        assert response.status_code == 200

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
    alias = "test_alias"
    invitation_response = await bob_member_client.post(f"{BASE_PATH}/create-invitation")
    invitation = invitation_response.json()

    accept_invite_json = AcceptInvitation(
        alias=alias,
        invitation=invitation["invitation"],
    ).model_dump()

    accept_response = await alice_member_client.post(
        f"{BASE_PATH}/accept-invitation",
        json=accept_invite_json,
    )
    connection_record = accept_response.json()

    assert_that(connection_record).contains(
        "connection_id", "state", "created_at", "updated_at", "invitation_key"
    )
    assert_that(connection_record).has_state("request-sent")
    assert_that(connection_record["alias"]).is_equal_to(alias)

    assert await check_webhook_state(
        client=alice_member_client,
        topic="connections",
        state="completed",
        filter_map={
            "connection_id": connection_record["connection_id"],
        },
    )


@pytest.mark.anyio
async def test_get_connections(
    bob_member_client: RichAsyncClient,
    alice_member_client: RichAsyncClient,
    bob_and_alice_connection: BobAliceConnect,  # pylint: disable=unused-argument
):
    alice_connections = (await alice_member_client.get(f"{BASE_PATH}")).json()[0]
    bob_connections = (await bob_member_client.get(f"{BASE_PATH}")).json()[0]

    assert_that(len(alice_connections)).is_greater_than_or_equal_to(1)
    assert_that(len(bob_connections)).is_greater_than_or_equal_to(1)

    alice_initation_msg_id = alice_connections["invitation_msg_id"]
    alice_did = alice_connections["my_did"]

    alice_alias = (await alice_member_client.get(f"{BASE_PATH}?alias=alice")).json()[0][
        "alias"
    ]
    assert alice_alias == "alice"

    alice_state = (
        await alice_member_client.get(f"{BASE_PATH}?state=completed")
    ).json()[0]["state"]
    assert alice_state == "completed"

    alice_key = (
        await alice_member_client.get(
            f"{BASE_PATH}?invitation_key={bob_connections['invitation_key']}"
        )
    ).json()[0]["invitation_key"]
    assert alice_key == alice_connections["invitation_key"]

    alice_invitation_msg_id = (
        await alice_member_client.get(
            f"{BASE_PATH}?invitation_msg_id={alice_initation_msg_id}"
        )
    ).json()[0]["invitation_msg_id"]
    assert alice_invitation_msg_id == alice_initation_msg_id

    alice_my_did = (
        await alice_member_client.get(f"{BASE_PATH}?my_did={alice_did}")
    ).json()[0]["my_did"]
    assert alice_my_did == alice_did

    alice_their_did = (
        await alice_member_client.get(
            f"{BASE_PATH}?their_did={bob_connections['my_did']}"
        )
    ).json()[0]["their_did"]
    assert alice_their_did == alice_connections["their_did"]

    with pytest.raises(HTTPException) as exc:
        await alice_member_client.get(
            f"{BASE_PATH}?their_public_did={bob_connections['their_public_did']}"
        )
    assert exc.value.status_code == 422

    alice_their_role = (
        await alice_member_client.get(f"{BASE_PATH}?their_role=inviter")
    ).json()[0]["their_role"]
    assert alice_their_role == "inviter"


@pytest.mark.anyio
async def test_get_connection_by_id(
    bob_member_client: RichAsyncClient,
):
    invitation_response = await bob_member_client.post(f"{BASE_PATH}/create-invitation")
    invitation = invitation_response.json()
    connection_id = invitation["connection_id"]

    connection_response = await bob_member_client.get(f"{BASE_PATH}/{connection_id}")
    connection_record = connection_response.json()

    assert_that(connection_response.status_code).is_equal_to(200)
    assert_that(connection_record).contains(
        "connection_id", "state", "created_at", "updated_at", "invitation_key"
    )


@pytest.mark.anyio
async def test_delete_connection(
    bob_member_client: RichAsyncClient,
):
    invitation_response = await bob_member_client.post(f"{BASE_PATH}/create-invitation")
    invitation = invitation_response.json()
    connection_id = invitation["connection_id"]

    response = await bob_member_client.delete(f"{BASE_PATH}/{connection_id}")
    assert_that(response.status_code).is_equal_to(200)

    with pytest.raises(HTTPException) as exc:
        response = await bob_member_client.get(f"{BASE_PATH}/{connection_id}")
    assert_that(exc.value.status_code).is_equal_to(404)


@pytest.mark.anyio
async def test_bob_and_alice_connect(
    bob_member_client: RichAsyncClient,
    alice_member_client: RichAsyncClient,
):
    invitation_response = await bob_member_client.post(
        f"{BASE_PATH}/create-invitation",
    )
    invitation = invitation_response.json()

    accept_response = await alice_member_client.post(
        f"{BASE_PATH}/accept-invitation",
        json={"invitation": invitation["invitation"]},
    )
    connection_record = accept_response.json()

    assert await check_webhook_state(
        client=alice_member_client,
        topic="connections",
        state="completed",
        filter_map={
            "connection_id": connection_record["connection_id"],
        },
    )

    alice_connection_id = connection_record["connection_id"]
    bob_connection_id = invitation["connection_id"]

    bob_connection = (
        await bob_member_client.get(f"{BASE_PATH}/{bob_connection_id}")
    ).json()
    alice_connection = (
        await alice_member_client.get(f"{BASE_PATH}/{alice_connection_id}")
    ).json()

    assert "completed" in alice_connection["state"]
    assert "completed" in bob_connection["state"]
