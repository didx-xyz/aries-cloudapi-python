import asyncio
import logging
from asyncio import TimeoutError

import pytest
from httpx import AsyncClient

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
async def test_enqueue_sse_event(sse_manager_fixture):
    mock_service = AsyncMock()
    mock_service.get_undelivered_messages.return_value = []
    topic = "test-topic"
    wallet_id = "test-wallet"
    event = "test-message"

    async with sse_manager_fixture.sse_event_stream(
        wallet_id, topic, mock_service
    ) as queue:
        await sse_manager_fixture.enqueue_sse_event(
            event, wallet_id, topic, mock_service
        )
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
async def test_sse_subscribe(alice_member_client):
    async with AsyncClient(app=app, base_url=WEBHOOKS_URL) as async_client:
        # get the wallet_id of the faber_client
        wallet_id = get_wallet_id_from_async_client(alice_member_client)
        topic = WEBHOOK_TOPIC_ALL

        async with async_client.stream("GET", f"/sse/{topic}/{wallet_id}") as response:
            LOGGER.warning("IN EVENT")
            event = await response.aiter_text().__anext__()
            LOGGER.warning("GOT EVENT %s:", event)
            assert wallet_id in event

            # if you want to test the caching functionality
            # you can trigger another event here and make sure
            # the second event also shows up in the stream.
