import asyncio
import json
import time
from assertpy import assert_that

import pytest
from httpx import Response
from generic.messaging import Message, TrustPingMsg

APPLICATION_JSON_CONTENT_TYPE = {"content-type": "application/json"}
MESSAGE_PATH = "/generic/messaging"
BASE_PATH_CON = "/generic/connections"


@pytest.yield_fixture(scope="module")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
@pytest.mark.asyncio
async def create_bob_and_alice_connection(
    async_client_bob_module_scope, async_client_alice_module_scope
):
    async_client_bob = async_client_bob_module_scope
    async_client_alice = async_client_alice_module_scope
    """This test validates that bob and alice connect successfully...

    NB: it assumes you have all the "auto connection" settings flagged as on.

    ACAPY_AUTO_ACCEPT_INVITES=true
    ACAPY_AUTO_ACCEPT_REQUESTS=true
    ACAPY_AUTO_PING_CONNECTION=true

    """
    # create invitation on bob side
    invitation = (await async_client_bob.get(BASE_PATH_CON + "/create-invite")).json()
    bob_connection_id = invitation["connection_id"]
    connections = (await async_client_bob.get(BASE_PATH_CON)).json()
    assert_that(connections["results"]).extracting("connection_id").contains_only(
        bob_connection_id
    )

    # accept invitation on alice side
    invite_response = (
        await async_client_alice.post(
            BASE_PATH_CON + "/accept-invite", data=json.dumps(invitation["invitation"])
        )
    ).json()
    time.sleep(15)
    alice_connection_id = invite_response["connection_id"]
    # fetch and validate
    # both connections should be active - we have waited long enough for events to be exchanged
    # and we are running in "auto connect" mode.
    bob_connections = (await async_client_bob.get(BASE_PATH_CON)).json()
    alice_connections = (await async_client_alice.get(BASE_PATH_CON)).json()

    assert_that(bob_connections["results"]).extracting("connection_id").contains(
        bob_connection_id
    )
    bob_connection = [
        c for c in bob_connections["results"] if c["connection_id"] == bob_connection_id
    ][0]
    assert_that(bob_connection).has_state("active")

    assert_that(alice_connections["results"]).extracting("connection_id").contains(
        alice_connection_id
    )
    alice_connection = [
        c
        for c in alice_connections["results"]
        if c["connection_id"] == alice_connection_id
    ][0]
    assert_that(alice_connection).has_state("active")

    return {
        "alice_connection_id": alice_connection_id,
        "bob_connection_id": bob_connection_id,
    }


@pytest.fixture(scope="module")
def alice_conn_id(create_bob_and_alice_connection):
    return create_bob_and_alice_connection["alice_connection_id"]


@pytest.mark.asyncio()
async def test_send_trust_ping(alice_conn_id, async_client_alice_module_scope):
    message = TrustPingMsg(connection_id=alice_conn_id, comment_msg="Donda").json()
    response = await async_client_alice_module_scope.post(
        MESSAGE_PATH + "/trust-ping", data=message
    )
    assert type(response) is Response
    assert response.status_code == 200
    assert response.content != ""
    assert response.json()["thread_id"]


@pytest.mark.asyncio()
async def test_send_message(alice_conn_id, async_client_alice_module_scope):
    message = Message(connection_id=alice_conn_id, msg="Donda").json()
    response = await async_client_alice_module_scope.post(
        MESSAGE_PATH + "/send-message", data=message
    )
    assert type(response) is Response
    assert response.status_code == 200
    assert response.json() == {}
