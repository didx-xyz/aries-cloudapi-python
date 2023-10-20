import pytest
from assertpy.assertpy import assert_that

from app.models.messaging import Message, TrustPingMsg
from app.routes.messaging import router
from app.tests.util.ecosystem_connections import BobAliceConnect
from shared import RichAsyncClient

MESSAGING_BASE_PATH = router.prefix


@pytest.mark.anyio
async def test_send_trust_ping(
    bob_and_alice_connection: BobAliceConnect, alice_member_client: RichAsyncClient
):
    trustping_msg = TrustPingMsg(
        connection_id=bob_and_alice_connection.alice_connection_id, comment="Donda"
    )

    response = await alice_member_client.post(
        MESSAGING_BASE_PATH + "/trust-ping", json=trustping_msg.model_dump()
    )
    response_data = response.json()

    assert_that(response.status_code).is_equal_to(200)
    assert_that(response_data).contains("thread_id")


@pytest.mark.anyio
async def test_send_message(
    bob_and_alice_connection: BobAliceConnect, alice_member_client: RichAsyncClient
):
    message = Message(
        connection_id=bob_and_alice_connection.alice_connection_id, content="Donda"
    )

    response = await alice_member_client.post(
        MESSAGING_BASE_PATH + "/send-message", json=message.model_dump()
    )

    assert_that(response.status_code).is_equal_to(200)
