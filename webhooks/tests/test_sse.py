import json
import logging

import pytest
from httpx import AsyncClient, Response, Timeout

from app.tests.util.ecosystem_connections import BobAliceConnect
from app.tests.util.webhooks import get_wallet_id_from_async_client
from shared import WEBHOOKS_URL, RichAsyncClient

LOGGER = logging.getLogger(__name__)


@pytest.mark.anyio
async def test_sse_subscribe_wallet_topic(
    alice_member_client: RichAsyncClient,
    bob_and_alice_connection: BobAliceConnect,
):
    alice_wallet_id = get_wallet_id_from_async_client(alice_member_client)
    alice_connection_id = bob_and_alice_connection.alice_connection_id

    sse_response = await get_sse_stream_response(alice_wallet_id, topic="connections")
    LOGGER.debug("SSE stream response: %s", sse_response)
    json_lines = response_to_json(sse_response)
    LOGGER.debug("Response as json: %s", json_lines)
    assert any(
        line["topic"] == "connections"
        and line["wallet_id"] == alice_wallet_id
        and line["payload"]["connection_id"] == alice_connection_id
        for line in json_lines
    )


@pytest.mark.anyio
async def test_sse_subscribe_event(
    alice_member_client: RichAsyncClient,
    bob_and_alice_connection: BobAliceConnect,
):
    alice_wallet_id = get_wallet_id_from_async_client(alice_member_client)
    alice_connection_id = bob_and_alice_connection.alice_connection_id

    topic = "connections"
    field = "connection_id"
    state = "completed"

    url = f"{WEBHOOKS_URL}/sse/{alice_wallet_id}/{topic}/{field}/{alice_connection_id}/{state}"
    sse_response = await listen_for_event(url)
    LOGGER.debug("SSE stream response: %s", sse_response)

    assert (
        sse_response["topic"] == topic
        and sse_response["wallet_id"] == alice_wallet_id
        and sse_response["payload"][field] == alice_connection_id
        and sse_response["payload"]["state"] == state
    )


@pytest.mark.anyio
async def test_sse_subscribe_state(
    alice_member_client: RichAsyncClient,
    bob_and_alice_connection: BobAliceConnect,
):
    alice_wallet_id = get_wallet_id_from_async_client(alice_member_client)
    alice_connection_id = bob_and_alice_connection.alice_connection_id

    topic = "connections"
    state = "completed"

    url = f"{WEBHOOKS_URL}/sse/{alice_wallet_id}/{topic}/{state}"
    sse_response = await listen_for_event(url)
    LOGGER.debug("SSE stream response: %s", sse_response)

    assert (
        sse_response["topic"] == topic
        and sse_response["wallet_id"] == alice_wallet_id
        and sse_response["payload"]["state"] == state
        and sse_response["payload"]["connection_id"] == alice_connection_id
    )


async def get_sse_stream_response(wallet_id, topic, duration=10) -> Response:
    timeout = Timeout(duration)
    async with AsyncClient(timeout=timeout) as client:
        async with client.stream(
            "GET", f"{WEBHOOKS_URL}/sse/{wallet_id}/{topic}"
        ) as response:
            response_text = ""
            try:
                async for line in response.aiter_lines():
                    response_text += line
            except TimeoutError:
                pass  # Timeout reached, return the response text read so far
            return response_text


def response_to_json(response_text):
    # Split the response into lines
    lines = response_text.split("data: ")

    # # Parse each line as JSON
    json_lines = [json.loads(line) for line in lines if line]

    return json_lines


async def listen_for_event(url, duration=10):
    timeout = Timeout(duration)
    async with AsyncClient(timeout=timeout) as client:
        async with client.stream("GET", url) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    return json.loads(data)
                elif line == "" or line.startswith(": ping"):
                    pass  # ignore newlines and pings
                else:
                    LOGGER.warning("Unexpected SSE line: %s", line)
