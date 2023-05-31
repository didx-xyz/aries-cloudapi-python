import logging
from typing import Any, Generator
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from dependency_injector.containers import DeclarativeContainer
from dependency_injector.providers import Factory
from dependency_injector.wiring import inject
from fastapi import FastAPI

from app.constants import WEBHOOKS_URL
from app.tests.util.webhooks import get_wallet_id_from_async_client
from shared_models import WEBHOOK_TOPIC_ALL
from webhooks.server_sent_events import get_sse_manager, router
from webhooks.services import Service
from webhooks.sse_manager import SSEManager

LOGGER = logging.getLogger(__name__)


@pytest.fixture
async def sse_manager() -> Generator[SSEManager, Any, None]:
    yield SSEManager()


@pytest.mark.anyio
async def test_enqueue_sse_event(sse_manager):
    mock_service = AsyncMock()
    mock_service.get_undelivered_messages.return_value = []
    topic = "test-topic"
    wallet_id = "test-wallet"
    event = "test-message"

    async with sse_manager.sse_event_stream(wallet_id, topic, mock_service) as queue:
        await sse_manager.enqueue_sse_event(event, wallet_id, topic, mock_service)
        message = await queue.get()
        assert message == event


class TestContainer(DeclarativeContainer):
    service = Factory(Service)
    sse_manager = Factory(get_sse_manager)


app = FastAPI()
app.container = TestContainer()
app.dependency_overrides[SSEManager] = TestContainer.sse_manager
app.dependency_overrides[Service] = TestContainer.service

app.include_router(router)


@pytest.mark.anyio
async def test_sse_subscribe(alice_member_client, acme_and_alice_connection):
    async with httpx.AsyncClient(app=app, base_url=WEBHOOKS_URL) as ac:
        # get the wallet_id of the faber_client
        wallet_id = get_wallet_id_from_async_client(alice_member_client)
        topic = WEBHOOK_TOPIC_ALL

        async with ac.stream("GET", f"/sse/{topic}/{wallet_id}") as response:
            LOGGER.warning("IN EVENT")
            event = await response.aiter_text().__anext__()
            LOGGER.warning("GOT EVENT %s:", event)
            assert wallet_id in event

            # if you want to test the caching functionality
            # you can trigger another event here and make sure
            # the second event also shows up in the stream.
