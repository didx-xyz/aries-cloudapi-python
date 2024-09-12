from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from waypoint.main import app, app_lifespan, health_live, health_ready
from waypoint.routes import sse
from waypoint.services.nats_service import NatsEventsProcessor


def test_create_app():
    assert app.title == "Waypoint Service"
    routes = [route.path for route in app.routes]

    routers = [sse]
    nested_list = [m.router.routes for m in routers]
    flattened_routers_list = [item for sublist in nested_list for item in sublist]
    expected_routes = [r.path for r in flattened_routers_list] + [
        "/health/ready",
        "/health/live",
    ]
    for route in expected_routes:
        assert route in routes


@pytest.fixture
def nats_events_processor_mock():
    mock = AsyncMock(spec=NatsEventsProcessor)
    return mock


@pytest.mark.anyio
async def test_app_lifespan(
    nats_events_processor_mock,  # pylint: disable=redefined-outer-name
):
    container_mock = AsyncMock(
        nats_events_processor=AsyncMock(return_value=nats_events_processor_mock),
        wire=MagicMock(),
        shutdown_resources=AsyncMock(),
    )
    with patch("waypoint.main.Container", return_value=container_mock):
        async with app_lifespan(FastAPI()):
            pass

        container_mock.wire.assert_called_once()
        container_mock.nats_events_processor.assert_called_once()
        container_mock.shutdown_resources.assert_called_once()


@pytest.mark.anyio
async def test_health_live():
    response = await health_live()
    assert response == {"status": "live"}


@pytest.mark.anyio
async def test_health_ready():
    response = await health_ready()
    assert response == {"status": "ready"}
