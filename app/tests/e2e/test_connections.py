import time
import json
import time

import pytest
import httpx
from assertpy import assert_that
from httpx import AsyncClient

# This import is important for tests to run!
from app.tests.util.member_personas import BobAliceConnect, BobAlicePublicDid
from app.tests.util.event_loop import event_loop

from app.tests.util.string import get_wallet_id_from_JWT


@pytest.mark.asyncio
async def test_create_invitation(
    bob_member_client: AsyncClient,
):
    response = await bob_member_client.post("/generic/connections/create-invitation")
    invitation = response.json()

    assert_that(invitation["connection_id"]).is_not_empty()
    assert_that(invitation["invitation"]).is_instance_of(dict).contains(
        "@id", "@type", "recipientKeys", "serviceEndpoint"
    )
    assert_that(invitation["invitation_url"]).contains("http://")


@pytest.mark.asyncio
async def test_accept_invitation(
    bob_member_client: AsyncClient,
    alice_member_client: AsyncClient,
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
    state = connection_record["state"]

    wallet_id = get_wallet_id_from_JWT(alice_member_client)

    t_end = time.time() + 10
    while time.time() < t_end:
        conns = (httpx.get(f"http://localhost:3010/connections/{wallet_id}")).json()
        states = [
            d["payload"]["state"]
            for d in conns
            # if d["payload"]["connection_id"] == connection_record["connection_id"]
        ]
        time.sleep(1)
        if "active" in states:
            break
        # state = conns[-1]["payload"]["state"]
        # print(conns)

    assert_that(connection_record).contains(
        "connection_id", "state", "created_at", "updated_at", "invitation_key"
    )
    assert_that(connection_record).has_state("request-sent")


@pytest.mark.asyncio
async def test_get_connections(
    bob_member_client: AsyncClient,
    alice_member_client: AsyncClient,
    bob_and_alice_connection: BobAliceConnect,
):
    alice_connections = (await alice_member_client.get("/generic/connections")).json()
    bob_connections = (await bob_member_client.get("/generic/connections")).json()

    assert_that(len(alice_connections)).is_greater_than_or_equal_to(1)
    assert_that(len(bob_connections)).is_greater_than_or_equal_to(1)


@pytest.mark.asyncio
async def test_get_connection_by_id(
    bob_member_client: AsyncClient,
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


@pytest.mark.asyncio
async def test_delete_connection(
    bob_member_client: AsyncClient,
):
    invitation_response = await bob_member_client.post(
        "/generic/connections/create-invitation"
    )
    invitation = invitation_response.json()
    connection_id = invitation["connection_id"]

    response = await bob_member_client.delete(f"/generic/connections/{connection_id}")
    assert_that(response.status_code).is_equal_to(200)

    response = await bob_member_client.get(f"/generic/connections/{connection_id}")
    assert_that(response.status_code).is_equal_to(404)


@pytest.mark.asyncio
async def test_bob_and_alice_connect(
    bob_member_client: AsyncClient,
    alice_member_client: AsyncClient,
    bob_and_alice_connection: BobAliceConnect,
):
    bob_connection = (await bob_member_client.get(f"/generic/connections")).json()[0]
    alice_connection = (await alice_member_client.get(f"/generic/connections")).json()[
        0
    ]

    assert_that(bob_connection).has_state("completed")
    assert_that(alice_connection).has_state("completed")


@pytest.mark.asyncio
async def test_create_invitation_oob(
    bob_member_client: AsyncClient,
):

    invitation_response = await bob_member_client.post(
        "/generic/connections/oob/create-invitation", json={"create_connection": True}
    )
    assert_that(invitation_response.status_code).is_equal_to(200)
    invitation = invitation_response.json()

    assert_that(invitation).contains("invi_msg_id", "invitation", "invitation_url")
    assert_that(invitation["invitation"]).contains("@id", "services")


@pytest.mark.asyncio
async def test_accept_invitation_oob(
    bob_member_client: AsyncClient,
):
    invitation_response = await bob_member_client.post(
        "/generic/connections/oob/create-invitation", json={"create_connection": True}
    )
    assert_that(invitation_response.status_code).is_equal_to(200)
    invitation = invitation_response.json()

    accept_response = await bob_member_client.post(
        "/generic/connections/oob/accept-invitation",
        json={"invitation": invitation["invitation"]},
    )
    connection_record = accept_response.json()

    assert_that(accept_response.status_code).is_equal_to(200)
    assert_that(connection_record).contains(
        "connection_id", "state", "created_at", "updated_at", "invitation_key"
    )
    assert_that(connection_record).has_connection_protocol("didexchange/1.0")


@pytest.mark.asyncio
async def test_oob_connect_via_public_did(
    bob_member_client: AsyncClient,
    alice_member_client: AsyncClient,
    bob_and_alice_public_did: BobAlicePublicDid,
):
    time.sleep(5)
    connect_response = await bob_member_client.post(
        "/generic/connections/oob/connect-public-did",
        json={"public_did": bob_and_alice_public_did["alice_public_did"]},
    )
    connection_record = connect_response.json()

    time.sleep(5)

    assert_that(connection_record).has_their_public_did(
        bob_and_alice_public_did["alice_public_did"]
    )

    public_did_response = await alice_member_client.get("/wallet/dids/public")
    alice_public_did = public_did_response.json()

    alice_connections_response = await alice_member_client.get("/generic/connections")
    alice_connections = alice_connections_response.json()

    # Check that a connection exists where the invitation key is the verkey of alice's public did
    assert_that(alice_connections).extracting("invitation_key").contains(
        alice_public_did["verkey"]
    )
