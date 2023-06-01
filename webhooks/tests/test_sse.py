import asyncio
import json
import logging

import pytest
from httpx import AsyncClient, Response

from app.constants import WEBHOOKS_URL
from app.tests.util.ecosystem_connections import BobAliceConnect
from app.tests.util.webhooks import get_wallet_id_from_async_client
from app.util.rich_async_client import RichAsyncClient
from webhooks.dependencies import sse_manager
from webhooks.dependencies.container import Container, get_container
from webhooks.dependencies.sse_manager import SSEManager
from webhooks.main import app

LOGGER = logging.getLogger(__name__)


def init_container() -> Container:
    container = get_container()
    container.wire(modules=[__name__, sse_manager])
    return container


@pytest.fixture
async def get_sse_manager():
    container = init_container()
    return SSEManager(container.service)


@pytest.mark.anyio
async def test_sse_subscribe_wallet(
    alice_member_client: RichAsyncClient,
    bob_and_alice_connection: BobAliceConnect,
    get_sse_manager: SSEManager,
):
    alice_wallet_id = get_wallet_id_from_async_client(alice_member_client)

    async with AsyncClient(app=app, base_url=WEBHOOKS_URL) as client:
        try:
        except asyncio.TimeoutError:
            pytest.fail("Test timed out before an event was received.")

        # Create an async function to check the response
        async def check_response(response):
            results = []
            async for data in response.text.split("\n"):
                if data["id"] != "[]":
                    results.append(data)
                    break
            return results

        try:
            # Use asyncio.wait_for to set a timeout
            result = await asyncio.wait_for(check_response(response), timeout=10)
            assert alice_wallet_id in result[0]
        except TimeoutError:
            pytest.fail("Test timed out before an event was received.")
