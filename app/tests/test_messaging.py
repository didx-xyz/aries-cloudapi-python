import asyncio

import pytest
from httpx import AsyncClient, Response

from app.generic.messaging import Message, TrustPingMsg

APPLICATION_JSON_CONTENT_TYPE = {"content-type": "application/json"}
MESSAGE_PATH = "/generic/messaging"
BASE_PATH_CON = "/generic/connections"


@pytest.yield_fixture(scope="module")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio()
async def test_send_trust_ping(
    alice_connection_id: str, async_client_alice_module_scope: AsyncClient
):
    trustping_msg = TrustPingMsg(
        connection_id=alice_connection_id, comment="Donda"
    ).dict()
    response = await async_client_alice_module_scope.post(
        MESSAGE_PATH + "/trust-ping", json=trustping_msg
    )
    assert type(response) is Response
    assert response.status_code == 200
    assert response.content != ""
    assert response.json()["thread_id"]


@pytest.mark.asyncio()
async def test_send_message(
    alice_connection_id: str, async_client_alice_module_scope: AsyncClient
):
    message = Message(connection_id=alice_connection_id, content="Donda").dict()
    response = await async_client_alice_module_scope.post(
        MESSAGE_PATH + "/send-message", json=message
    )
    assert type(response) is Response
    assert response.status_code == 200
    assert response.json() == {}
