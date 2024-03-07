from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import FastAPI

from endorser.main import app, app_lifespan


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
