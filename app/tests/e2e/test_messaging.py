import pytest
from assertpy.assertpy import assert_that

from app.generic.messaging import Message, TrustPingMsg
from app.tests.util.ecosystem_connections import BobAliceConnect
from app.util.rich_async_client import RichAsyncClient


@pytest.mark.anyio
async def test_send_trust_ping(
    bob_and_alice_connection: BobAliceConnect, alice_member_client: RichAsyncClient
):
    trustping_msg = TrustPingMsg(
        connection_id=bob_and_alice_connection["alice_connection_id"], comment="Donda"
    )

    response = await alice_member_client.post(
        "/generic/messaging/trust-ping", json=trustping_msg.dict()
    )
    response_data = response.json()

    assert_that(response.status_code).is_equal_to(200)
    assert_that(response_data).contains("thread_id")


@pytest.mark.anyio
async def test_send_message(
    bob_and_alice_connection: BobAliceConnect, alice_member_client: RichAsyncClient
):
    message = Message(
        connection_id=bob_and_alice_connection["alice_connection_id"], content="Donda"
    )

    response = await alice_member_client.post(
        "/generic/messaging/send-message", json=message.dict()
    )

    assert_that(response.status_code).is_equal_to(200)
