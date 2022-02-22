import time
from typing import TypedDict

import pytest
from aries_cloudcontroller import AcaPyClient
from assertpy import assert_that
from httpx import AsyncClient

from app.tests.util.client import (
    member_acapy_client,
    member_admin_client,
    member_client,
)
from app.tests.util.ledger import create_public_did

from .tenants import create_tenant, delete_tenant


class BobAliceConnect(TypedDict):
    alice_connection_id: str
    bob_connection_id: str


class BobAlicePublicDid(TypedDict):
    bob_public_did: str
    alice_public_did: str


@pytest.fixture(scope="module")
async def bob_member_client():
    async with member_admin_client() as client:
        tenant = await create_tenant(client, "bob")

        yield member_client(token=tenant["access_token"])

        await delete_tenant(client, tenant["tenant_id"])


@pytest.fixture(scope="module")
async def alice_member_client():
    async with member_admin_client() as client:
        tenant = await create_tenant(client, "alice")

        yield member_client(token=tenant["access_token"])

        await delete_tenant(client, tenant["tenant_id"])


@pytest.fixture(scope="module")
async def bob_acapy_client(bob_member_client: AsyncClient):
    # We extract the token from the x-api-key header as that's the easiest
    # method to create an AcaPyClient from an AsyncClient
    [_, token] = bob_member_client.headers.get("x-api-key").split(".", maxsplit=1)

    client = member_acapy_client(token=token)
    yield client

    await client.close()


@pytest.fixture(scope="module")
async def alice_acapy_client(alice_member_client: AsyncClient):
    [_, token] = alice_member_client.headers.get("x-api-key").split(".", maxsplit=1)

    client = member_acapy_client(token=token)
    yield client

    await client.close()


@pytest.fixture(scope="module")
async def bob_and_alice_public_did(
    alice_acapy_client: AcaPyClient,
    bob_acapy_client: AcaPyClient,
) -> BobAlicePublicDid:
    bob_did = await create_public_did(bob_acapy_client)
    alice_did = await create_public_did(alice_acapy_client)

    return {
        "bob_public_did": bob_did.did,
        "alice_public_did": alice_did.did,
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
