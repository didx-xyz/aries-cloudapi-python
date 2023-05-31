from unittest import mock

import pytest
from httpx import AsyncClient

from webhooks.main import app, container
from webhooks.services import Service


@pytest.fixture
def client():
    client = AsyncClient(app=app, base_url="http://test")
    yield client


@pytest.mark.anyio
async def test_index(client):
    service_mock = mock.AsyncMock(spec=Service)
    service_mock.add_topic_entry.return_value = None
    service_mock.get_all_by_wallet.return_value = {"test": "Foo"}

    with container.service.override(service_mock):
        response = await client.get("/test")

    assert response.status_code == 200
    assert response.json() == {"test": "Foo"}
