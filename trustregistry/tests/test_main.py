import pytest

from shared import TRUST_REGISTRY_URL
from shared.util.rich_async_client import RichAsyncClient
from trustregistry.main import create_app
from trustregistry.registry import registry_actors, registry_schemas


def test_create_app():
    app = create_app()
    assert app.title == "Trust Registry"

    # Verifying that all routes are included
    routes = [route.path for route in app.routes]
    expected_routes = [
        r.path for r in (registry_actors.router.routes + registry_schemas.router.routes)
    ]
    for route in expected_routes:
        assert route in routes


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
