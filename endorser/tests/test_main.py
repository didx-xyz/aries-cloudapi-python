from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import FastAPI, HTTPException

from endorser.main import app, app_lifespan, health_check


def test_create_app():
    assert app.title == "Aries Cloud API: Endorser Service"

    # Verifying that all routes are included

    # Get all routes in app
    routes = [route.path for route in app.routes]

    expected_routes = "/health"
    assert expected_routes in routes


@pytest.mark.anyio
async def test_app_lifespan():
    # Mocks for services and container
    endorsement_processor_mock = MagicMock(start=Mock(), stop=AsyncMock())
    container_mock = MagicMock(
        endorsement_processor=MagicMock(return_value=endorsement_processor_mock),
        wire=MagicMock(),
        shutdown_resources=Mock(),
    )

    # Patch the get_container function to return the mocked container
    with patch("endorser.main.get_container", return_value=container_mock):
        # Run the app_lifespan context manager
        async with app_lifespan(FastAPI()):
            pass

        # Assert the container was wired with the correct modules
        container_mock.wire.assert_called_once()

        # Assert the endorsement_processor's start method was called
        endorsement_processor_mock.start.assert_called_once()

        # Assert the shutdown logic was called correctly
        endorsement_processor_mock.stop.assert_awaited_once()
        container_mock.shutdown_resources.assert_called_once()


@pytest.mark.anyio
async def test_health_check_healthy():
    endorsement_processor_mock = MagicMock(start=Mock(), stop=AsyncMock())
    endorsement_processor_mock.are_tasks_running.return_value = True

    response = await health_check(endorsement_processor=endorsement_processor_mock)
    assert response == {"status": "healthy"}


@pytest.mark.anyio
async def test_health_check_unhealthy():
    endorsement_processor_mock = MagicMock(start=Mock(), stop=AsyncMock())
    endorsement_processor_mock.are_tasks_running.return_value = False

    with pytest.raises(HTTPException) as exc_info:
        await health_check(endorsement_processor=endorsement_processor_mock)
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "One or more background tasks are not running."
