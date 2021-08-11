import pytest
from httpx import Response
from generic.messaging import Message, TrustPingMsg
from .test_issuer_v1 import (
    create_bob_and_alice_connect,
    event_loop,
    alice_connection_id,
)

APPLICATION_JSON_CONTENT_TYPE = {"content-type": "application/json"}
MESSAGE_PATH = "/generic/messaging"
BASE_PATH_CON = "/generic/connections"


@pytest.mark.asyncio()
async def test_send_trust_ping(alice_connection_id, async_client_alice_module_scope):
    message = TrustPingMsg(
        connection_id=alice_connection_id, comment_msg="Donda"
    ).json()
    response = await async_client_alice_module_scope.post(
        MESSAGE_PATH + "/trust-ping", data=message
    )
    assert type(response) is Response
    assert response.status_code == 200
    assert response.content != ""
    assert response.json()["thread_id"]


@pytest.mark.asyncio()
async def test_send_message(alice_connection_id, async_client_alice_module_scope):
    message = Message(connection_id=alice_connection_id, msg="Donda").json()
    response = await async_client_alice_module_scope.post(
        MESSAGE_PATH + "/send-message", data=message
    )
    assert type(response) is Response
    assert response.status_code == 200
    assert response.json() == {}
