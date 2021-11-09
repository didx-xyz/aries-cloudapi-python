import time
from contextlib import asynccontextmanager
from typing import Any, Dict, Tuple

import pytest
from aries_cloudcontroller import DIDResult
from assertpy import assert_that
from httpx import AsyncClient

import app.dependencies as dependencies
import app.generic.connections.connections as test_module
import app.tests.utils_test as test_utils
from app.facades.acapy_ledger import create_pub_did
from app.generic.connections.connections import (
    AcceptInvitation,
    AcceptOobInvitation,
    ConnectToPublicDid,
    CreateOobInvitation,
)
from app.generic.connections.models import Connection
from app.tests.utils_test import CONNECTIONS_BASE_PATH

INVITATION_A = ""
CreateWalletsMock = Tuple[Dict[str, Any], Dict[str, Any]]


async def token_responses(
    async_client: AsyncClient, create_wallets_mock: CreateWalletsMock
):
    yoda, han = create_wallets_mock

    yoda_wallet_id = yoda["wallet_id"]
    han_wallet_id = han["wallet_id"]

    yoda_token = await test_utils.get_wallet_token(async_client, yoda_wallet_id)
    han_token = await test_utils.get_wallet_token(async_client, han_wallet_id)

    return yoda_token, yoda_wallet_id, han_token, han_wallet_id


@pytest.fixture(name="create_wallets_mock")
async def fixture_create_wallets_mock(async_client: AsyncClient):
    yoda_wallet_response = await test_utils.create_wallet(async_client, "yoda")
    yoda_wallet_response = yoda_wallet_response.json()
    yoda_wallet_id = yoda_wallet_response["wallet_id"]

    han_wallet_response = await test_utils.create_wallet(async_client, "han")
    han_wallet_response = han_wallet_response.json()
    han_wallet_id = han_wallet_response["wallet_id"]
    yield yoda_wallet_response, han_wallet_response

    yoda_response = await test_utils.remove_wallet(async_client, yoda_wallet_id)
    han_response = await test_utils.remove_wallet(async_client, han_wallet_id)

    assert yoda_response.status_code == 200
    assert yoda_response.json() == {"status": "Successfully removed wallet"}
    assert han_response.status_code == 200
    assert han_response.json() == {"status": "Successfully removed wallet"}


@pytest.mark.asyncio
async def test_create_invitation(
    async_client: AsyncClient, create_wallets_mock: CreateWalletsMock
):
    yoda, _ = create_wallets_mock

    yoda_wallet_id = yoda["settings"]["wallet.id"]
    yoda_token = await test_utils.get_wallet_token(async_client, yoda_wallet_id)

    async with asynccontextmanager(dependencies.member_agent)(
        x_auth=f"Bearer {yoda_token}"
    ) as member_agent:
        invitation_creation_response = (
            await test_module.create_invitation(aries_controller=member_agent)
        ).dict()
    assert (
        invitation_creation_response["connection_id"]
        and invitation_creation_response["connection_id"] != {}
    )
    assert (
        invitation_creation_response["invitation"]
        and invitation_creation_response["invitation"] != {}
    )
    assert (
        invitation_creation_response["invitation"]["id"]
        and invitation_creation_response["invitation"]["id"] != {}
    )


@pytest.mark.asyncio
async def test_accept_invitation(
    async_client: AsyncClient, create_wallets_mock: CreateWalletsMock
):
    yoda_token, _, han_token, _ = await token_responses(
        async_client, create_wallets_mock
    )

    invitation = await test_utils.create_invitation(async_client, yoda_token)

    async with asynccontextmanager(dependencies.member_agent)(
        x_auth=f"Bearer {han_token}"
    ) as member_agent:
        accept_invitation_response = (
            await test_module.accept_invitation(
                body=AcceptInvitation(invitation=invitation),
                aries_controller=member_agent,
            )
        ).dict()

    assert (
        accept_invitation_response["created_at"]
        and accept_invitation_response["created_at"] != ""
    )
    assert (
        accept_invitation_response["invitation_key"]
        and accept_invitation_response["invitation_key"] != ""
    )


@pytest.mark.asyncio
async def test_get_connections(
    async_client: AsyncClient, create_wallets_mock: CreateWalletsMock
):
    yoda_token, _, han_token, _ = await token_responses(
        async_client, create_wallets_mock
    )

    invitation = await test_utils.create_invitation(async_client, yoda_token)

    async with asynccontextmanager(dependencies.member_agent)(
        x_auth=f"Bearer {han_token}"
    ) as member_agent:
        await test_module.accept_invitation(
            body=AcceptInvitation(invitation=invitation), aries_controller=member_agent
        )
        connections = await test_module.get_connections(aries_controller=member_agent)

    assert connections and len(connections) >= 1
    assert connections[0].connection_id and connections[0].connection_id != ""
    assert connections[0].created_at and connections[0].created_at != ""
    assert connections[0].invitation_key and connections[0].invitation_key != ""


@pytest.mark.asyncio
async def test_get_connection_by_id(
    async_client: AsyncClient, create_wallets_mock: CreateWalletsMock
):
    yoda_token, _, han_token, _ = await token_responses(
        async_client, create_wallets_mock
    )

    invitation = await test_utils.create_invitation(async_client, yoda_token)

    async with asynccontextmanager(dependencies.member_agent)(
        x_auth=f"Bearer {han_token}"
    ) as member_agent:
        await test_module.accept_invitation(
            body=AcceptInvitation(invitation=invitation), aries_controller=member_agent
        )
        connections = await test_module.get_connections(aries_controller=member_agent)
        connection_id = connections[0].connection_id
        connection_from_method = await test_module.get_connection_by_id(
            connection_id=connection_id, aries_controller=member_agent
        )
    assert connections[0] == connection_from_method


@pytest.mark.asyncio
async def test_delete_connection(
    async_client: AsyncClient, create_wallets_mock: CreateWalletsMock
):
    yoda_token, _, han_token, _ = await token_responses(
        async_client, create_wallets_mock
    )

    invitation = await test_utils.create_invitation(async_client, yoda_token)

    async with asynccontextmanager(dependencies.member_agent)(
        x_auth=f"Bearer {han_token}"
    ) as member_agent:
        await test_module.accept_invitation(
            body=AcceptInvitation(invitation=invitation), aries_controller=member_agent
        )
        connections = await test_module.get_connections(aries_controller=member_agent)
        connection_id = connections[0].connection_id
        await test_module.delete_connection_by_id(
            connection_id=connection_id, aries_controller=member_agent
        )
        connections = await test_module.get_connections(aries_controller=member_agent)
    assert connections == []


@pytest.mark.asyncio
async def test_bob_and_alice_connect(
    async_client_bob: AsyncClient, async_client_alice: AsyncClient
):
    """this test validates that bob and alice connect successfully"""

    # create invitation on bob side
    invitation = (
        await async_client_bob.post(f"{CONNECTIONS_BASE_PATH}/create-invitation")
    ).json()
    bob_connection_id = invitation["connection_id"]
    connections = (await async_client_bob.get(CONNECTIONS_BASE_PATH)).json()
    assert_that(connections).extracting("connection_id").contains_only(
        bob_connection_id
    )

    # accept invitation on alice side
    invitation_response = (
        await async_client_alice.post(
            f"{CONNECTIONS_BASE_PATH}/accept-invitation",
            json={"invitation": invitation["invitation"]},
        )
    ).json()
    alice_connection_id = invitation_response["connection_id"]

    # wait for events to be exchanged
    time.sleep(5)

    # fetch and validate
    # both connections should be active - we have waited long enough for events to be exchanged
    # and we are running in "auto connect" mode.
    bob_connections = (await async_client_bob.get(CONNECTIONS_BASE_PATH)).json()
    alice_connections = (await async_client_alice.get(CONNECTIONS_BASE_PATH)).json()

    assert_that(bob_connections).extracting("connection_id").contains(bob_connection_id)
    bob_connection = [
        c for c in bob_connections if c["connection_id"] == bob_connection_id
    ][0]
    assert_that(bob_connection).has_state("completed")

    assert_that(alice_connections).extracting("connection_id").contains(
        alice_connection_id
    )
    alice_connection = [
        c for c in alice_connections if c["connection_id"] == alice_connection_id
    ][0]
    assert_that(alice_connection).has_state("completed")


@pytest.mark.asyncio
async def test_bob_has_agent(async_client_bob: AsyncClient):
    assert_that(hasattr(async_client_bob, "agent")).is_true()
    assert_that(hasattr(async_client_bob.agent, "did")).is_true()
    assert_that(async_client_bob.agent.did).is_not_none()
    assert_that(async_client_bob.agent.headers).is_not_empty()
    assert_that(async_client_bob.agent.token).is_not_none()


@pytest.mark.asyncio
async def test_create_invitation_oob(
    async_client: AsyncClient, create_wallets_mock: CreateWalletsMock
):
    yoda, _ = create_wallets_mock

    yoda_wallet_id = yoda["settings"]["wallet.id"]
    yoda_token = await test_utils.get_wallet_token(async_client, yoda_wallet_id)

    async with asynccontextmanager(dependencies.ecosystem_agent)(
        x_auth=f"Bearer {yoda_token}"
    ) as ecosystem_agent:
        invitation_creation_response = (
            await test_module.create_oob_invitation(
                body=CreateOobInvitation(create_connection=True),
                aries_controller=ecosystem_agent,
            )
        ).dict()

    assert (
        invitation_creation_response["invi_msg_id"]
        and invitation_creation_response["invi_msg_id"] != ""
    )
    assert (
        invitation_creation_response["invitation"]
        and invitation_creation_response["invitation"] != {}
    )
    global INVITATION_A
    INVITATION_A = invitation_creation_response["invitation"]
    assert (
        invitation_creation_response["invitation"]["id"]
        and invitation_creation_response["invitation"]["id"] != ""
    )
    assert (
        invitation_creation_response["invitation"]["services"][0]["recipientKeys"]
        and invitation_creation_response["invitation"]["services"][0]["recipientKeys"]
        != []
    )


@pytest.mark.asyncio
async def test_accept_invitation_oob(
    async_client: AsyncClient, create_wallets_mock: CreateWalletsMock
):
    _, _, han_token, _ = await token_responses(async_client, create_wallets_mock)

    async with asynccontextmanager(dependencies.member_agent)(
        x_auth=f"Bearer {han_token}"
    ) as member_agent:
        accept_invitation_response = (
            await test_module.accept_oob_invitation(
                body=AcceptOobInvitation(invitation=INVITATION_A),
                aries_controller=member_agent,
            )
        ).dict()
    assert (
        accept_invitation_response["created_at"]
        and accept_invitation_response["created_at"] != ""
    )
    assert (
        accept_invitation_response["invitation_key"]
        and accept_invitation_response["invitation_key"] != ""
    )


@pytest.mark.asyncio
async def test_oob_connect_via_public_did(
    async_client: AsyncClient, create_wallets_mock: CreateWalletsMock
):
    yoda_token, _, han_token, _ = await token_responses(
        async_client, create_wallets_mock
    )

    async with asynccontextmanager(dependencies.member_agent)(
        x_auth=f"Bearer {yoda_token}"
    ) as member_agent:
        # CReate a new public DID and write it to ledger
        pub_did_yoda_res = (await create_pub_did(member_agent)).dict()
        # Use the new public DID as the DID and therefore as an implicit invitation
        pub_did_yoda = pub_did_yoda_res["did_object"]["did"]
        new_pub_did_as_invitation = await member_agent.wallet.set_public_did(
            did=pub_did_yoda
        )

    assert isinstance(new_pub_did_as_invitation, DIDResult)
    async with asynccontextmanager(dependencies.member_agent)(
        x_auth=f"Bearer {han_token}"
    ) as member_agent:
        han_dids = (await member_agent.wallet.get_dids()).dict()
        connection = await test_module.connect_to_public_did(
            body=ConnectToPublicDid(public_did=pub_did_yoda),
            aries_controller=member_agent,
        )
    # There is no public DID for han yet
    assert han_dids["results"] == []

    # We should have obtained a connection record
    assert isinstance(connection, Connection)
    connection = connection.dict()

    async with asynccontextmanager(dependencies.member_agent)(
        x_auth=f"Bearer {han_token}"
    ) as member_agent:
        # Now we should have a public did as we have a connection with yoda
        han_dids = [
            result["did"]
            for result in (await member_agent.wallet.get_dids()).dict()["results"]
        ]
    # Check our did is in our wallet and in the connection record
    assert connection["my_did"] in han_dids
    assert connection["their_public_did"] == pub_did_yoda
