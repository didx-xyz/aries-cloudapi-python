import pytest
from httpx import AsyncClient

from app.constants import TRUST_REGISTRY_URL


@pytest.mark.anyio
async def test_root():
    async with AsyncClient() as client:
        resp = await client.get(f"{TRUST_REGISTRY_URL}")

    assert resp.status_code == 200
    json_response = resp.json()
    assert all(key in json_response for key in ["actors", "schemas"])


@pytest.mark.anyio
async def test_registry():
    async with AsyncClient() as client:
        resp = await client.get(f"{TRUST_REGISTRY_URL}/registry")

    assert resp.status_code == 200
    json_response = resp.json()
    assert all(key in json_response for key in ["actors", "schemas"])
