from unittest import mock

import pytest
from httpx import AsyncClient

from main import app, container
from services import Service


@pytest.fixture
def client(event_loop):
    client = AsyncClient(app=app, base_url="http://test")
    yield client
    event_loop.run_until_complete(client.aclose())


@pytest.mark.asyncio
async def test_index(client):
    service_mock = mock.AsyncMock(spec=Service)
    service_mock.add_topic_entry.return_value = None
    service_mock.get_all_by_wallet.return_value = {"test": "Foo"}

    with container.service.override(service_mock):
        response = await client.get("/test")

    assert response.status_code == 200
    assert response.json() == {"test": "Foo"}
