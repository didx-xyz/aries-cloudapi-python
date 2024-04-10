from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import FastAPI, HTTPException

from webhooks.services.acapy_events_processor import AcaPyEventsProcessor
from webhooks.services.sse_manager import SseManager
from webhooks.web.main import app, app_lifespan, health_check
from webhooks.web.routers import sse, webhooks, websocket


def test_create_app():
    assert app.title == "Aries Cloud API: Webhooks and Server-Sent Events"

    # Verifying that all routes are included

    # Get all routes in app
    routes = [route.path for route in app.routes]

    # Get expected routes from all the routers
    routers = [sse, webhooks, websocket]
    nested_list = [m.router.routes for m in routers]
    flattened_routers_list = [item for sublist in nested_list for item in sublist]
    expected_routes = [r.path for r in flattened_routers_list] + ["/health"]
    for route in expected_routes:
        assert route in routes


@pytest.fixture
def acapy_events_processor_mock():
    mock = AsyncMock(spec=AcaPyEventsProcessor)
    return mock


@pytest.fixture
def sse_manager_mock():
    mock = AsyncMock(spec=SseManager)
    return mock


@pytest.mark.anyio
async def test_app_lifespan(
    acapy_events_processor_mock,  # pylint: disable=redefined-outer-name
    sse_manager_mock,  # pylint: disable=redefined-outer-name
):
    billing_processor_mock = MagicMock(start=Mock(), stop=AsyncMock())

    container_mock = MagicMock(
        acapy_events_processor=MagicMock(return_value=acapy_events_processor_mock),
        sse_manager=MagicMock(return_value=sse_manager_mock),
        billing_manager=MagicMock(return_value=billing_processor_mock),
        wire=MagicMock(),
        shutdown_resources=Mock(),
    )

    # Patch the Container to return the mocked container
    with patch("webhooks.web.main.Container", return_value=container_mock):
        # Run the app_lifespan context manager
        async with app_lifespan(FastAPI()):
            pass

        # Assert the container was wired with the correct modules
        container_mock.wire.assert_called_once()

        # Assert the endorsement_processor's start method was called
        sse_manager_mock.start.assert_called_once()
        acapy_events_processor_mock.start.assert_called_once()
        billing_processor_mock.start.assert_called_once()

        # Assert the shutdown logic was called correctly
        acapy_events_processor_mock.stop.assert_awaited_once()
        sse_manager_mock.stop.assert_awaited_once()
        billing_processor_mock.stop.assert_called_once()

        container_mock.shutdown_resources.assert_called_once()


@pytest.mark.anyio
async def test_health_check_healthy(
    acapy_events_processor_mock,  # pylint: disable=redefined-outer-name
    sse_manager_mock,  # pylint: disable=redefined-outer-name
):
    acapy_events_processor_mock.are_tasks_running.return_value = True
    sse_manager_mock.are_tasks_running.return_value = True

    response = await health_check(
        acapy_events_processor=acapy_events_processor_mock, sse_manager=sse_manager_mock
    )
    assert response == {"status": "healthy"}


@pytest.mark.anyio
async def test_health_check_unhealthy(
    acapy_events_processor_mock,  # pylint: disable=redefined-outer-name
    sse_manager_mock,  # pylint: disable=redefined-outer-name
):
    acapy_events_processor_mock.are_tasks_running.return_value = False
    sse_manager_mock.are_tasks_running.return_value = True
    with pytest.raises(HTTPException) as exc_info:
        await health_check(
            acapy_events_processor=acapy_events_processor_mock,
            sse_manager=sse_manager_mock,
        )
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "One or more background tasks are not running."

    acapy_events_processor_mock.are_tasks_running.return_value = True
    sse_manager_mock.are_tasks_running.return_value = False
    with pytest.raises(HTTPException) as exc_info:
        await health_check(
            acapy_events_processor=acapy_events_processor_mock,
            sse_manager=sse_manager_mock,
        )
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "One or more background tasks are not running."
