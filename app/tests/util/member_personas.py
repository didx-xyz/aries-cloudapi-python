from typing import TypedDict
import pytest
from httpx import AsyncClient
import time
from app.tests.util.client import member_client

from .client import member_admin_client
from .multitenant import create_member_wallet, delete_member_wallet
from .wallet import create_and_set_public_did
from assertpy import assert_that


class BobAliceConnect(TypedDict):
    alice_connection_id: str
    bob_connection_id: str


class BobAlicePublicDid(TypedDict):
    bob_public_did: str
    alice_public_did: str


@pytest.fixture(scope="module")
async def bob_member_client():
    client = member_admin_client()
    wallet = await create_member_wallet(client, "bob")

    yield member_client(token=wallet["token"])

    await delete_member_wallet(client, wallet["wallet_id"])


@pytest.fixture(scope="module")
async def alice_member_client():
    client = member_admin_client()
    wallet = await create_member_wallet(client, "alice")

    yield member_client(token=wallet["token"])

    await delete_member_wallet(client, wallet["wallet_id"])


@pytest.fixture(scope="module")
async def bob_and_alice_public_did(
    alice_member_client: AsyncClient, bob_member_client: AsyncClient
) -> BobAlicePublicDid:
    bob_did = await create_and_set_public_did(bob_member_client)
    alice_did = await create_and_set_public_did(alice_member_client)

    return {
        "bob_public_did": bob_did["did_object"]["did"],
        "alice_public_did": alice_did["did_object"]["did"],
    }


@pytest.fixture(scope="module")
async def bob_and_alice_connection(
    bob_member_client: AsyncClient,
    alice_member_client: AsyncClient,
) -> BobAliceConnect:
    # create invitation on bob side
    invitation = (
        await bob_member_client.post("/generic/connections/create-invitation")
    ).json()

    # accept invitation on alice side
    invitation_response = (
        await alice_member_client.post(
            "/generic/connections/accept-invitation",
            json={"invitation": invitation["invitation"]},
        )
    ).json()

    time.sleep(15)

    bob_connection_id = invitation["connection_id"]
    alice_connection_id = invitation_response["connection_id"]

    # fetch and validate
    # both connections should be active - we have waited long enough for events to be exchanged
    bob_connection = (
        await bob_member_client.get(f"/generic/connections/{bob_connection_id}")
    ).json()
    alice_connection = (
        await alice_member_client.get(f"/generic/connections/{alice_connection_id}")
    ).json()

    assert_that(bob_connection).has_state("completed")
    assert_that(alice_connection).has_state("completed")

    return {
        "alice_connection_id": alice_connection_id,
        "bob_connection_id": bob_connection_id,
    }
