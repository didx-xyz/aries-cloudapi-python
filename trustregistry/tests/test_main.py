import pytest

from shared import TRUST_REGISTRY_URL
from shared.util.rich_async_client import RichAsyncClient


@pytest.mark.anyio
async def test_root():
    async with RichAsyncClient() as client:
        resp = await client.get(f"{TRUST_REGISTRY_URL}")

    assert resp.status_code == 200
    json_response = resp.json()
    assert all(key in json_response for key in ["actors", "schemas"])


@pytest.mark.anyio
async def test_registry():
    async with RichAsyncClient() as client:
        resp = await client.get(f"{TRUST_REGISTRY_URL}/registry")

    assert resp.status_code == 200
    json_response = resp.json()
    assert all(key in json_response for key in ["actors", "schemas"])
