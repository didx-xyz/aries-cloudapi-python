import asyncio
import json
import logging

import pytest
from httpx import AsyncClient, Response

from app.tests.util.ecosystem_connections import BobAliceConnect
from app.tests.util.webhooks import get_wallet_id_from_async_client
from shared import WEBHOOKS_URL, RichAsyncClient
from webhooks.main import app

LOGGER = logging.getLogger(__name__)


@pytest.mark.anyio
async def test_sse_subscribe_wallet(
    alice_member_client: RichAsyncClient,
    bob_and_alice_connection: BobAliceConnect,
):
    alice_wallet_id = get_wallet_id_from_async_client(alice_member_client)
    alice_connection_id = bob_and_alice_connection.alice_connection_id

    sse_response = await asyncio.wait_for(
        get_sse_response(alice_wallet_id, topic="connections"), timeout=5
    )
    json_lines = response_to_json(sse_response)

    assert any(
        line["topic"] == "connections"
        and line["wallet_id"] == alice_wallet_id
        and line["payload"]["connection_id"] == alice_connection_id
        for line in json_lines
    )


async def get_sse_response(wallet_id, topic) -> Response:
    async with AsyncClient(app=app, base_url=WEBHOOKS_URL) as client:
        async with client.stream("GET", f"/sse/{wallet_id}/{topic}") as response:
            response_text = ""
            async for line in response.aiter_lines():
                response_text += line
            return response_text


def response_to_json(response_text):
    # Split the response into lines
    lines = response_text.split("data: ")

    # # Parse each line as JSON
    json_lines = [json.loads(line) for line in lines if line]

    return json_lines
