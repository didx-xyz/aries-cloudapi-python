from unittest.mock import AsyncMock

import pytest
from fastapi import BackgroundTasks, Request
from sse_starlette import EventSourceResponse

from shared.constants import DISCONNECT_CHECK_PERIOD
from webhooks.services.sse_manager import SseManager
from webhooks.web.routers.sse import (
    BadGroupIdException,
    check_disconnection,
    sse_subscribe_event_with_field_and_state,
    sse_subscribe_event_with_state,
    sse_subscribe_stream_with_fields,
    sse_subscribe_wallet,
    sse_subscribe_wallet_topic,
)


@pytest.fixture
def sse_manager_mock():
    mock = AsyncMock(spec=SseManager)
    return mock


import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi import Request


@pytest.mark.anyio
async def test_check_disconnection_disconnects():
    # Mock Request to simulate disconnection
    request = AsyncMock(spec=Request)
    request.is_disconnected.return_value = True

    stop_event = asyncio.Event()

    # Run check_disconnection in a background task
    task = asyncio.create_task(check_disconnection(request, stop_event))

    # Give it enough time to check for disconnection and set the stop event
    await asyncio.sleep(DISCONNECT_CHECK_PERIOD * 1.1)

    assert stop_event.is_set()  # Expect stop_event to be set upon disconnection
    assert task.done() is True


@pytest.mark.anyio
async def test_check_disconnection_stop_event():
    # Mock Request to stay connected
    request = AsyncMock(spec=Request)
    request.is_disconnected.return_value = False

    stop_event = asyncio.Event()

    # Run check_disconnection in a background task
    task = asyncio.create_task(check_disconnection(request, stop_event))

    # Assert still running after one check period
    await asyncio.sleep(DISCONNECT_CHECK_PERIOD * 1.1)
    assert task.done() is False

    # Simulate an external event causing the stop
    stop_event.set()

    # Wait a bit more to ensure the task respects the stop event
    await asyncio.sleep(DISCONNECT_CHECK_PERIOD)

    assert stop_event.is_set()  # The stop_event should still be set
    assert task.done() is True


@pytest.mark.anyio
@pytest.mark.parametrize("group_id", [None, "correct_group", "wrong_group"])
async def test_sse_subscribe_wallet(
    sse_manager_mock,  # pylint: disable=redefined-outer-name
    group_id,
):
    if group_id == "wrong_group":
        sse_manager_mock.check_wallet_belongs_to_group.return_value = False
    else:
        sse_manager_mock.check_wallet_belongs_to_group.return_value = True

    # Prepare the Request and BackgroundTasks objects
    request = Request(scope={"type": "http"})
    background_tasks = BackgroundTasks()

    # Call the sse_subscribe_wallet function with the mocked request and background tasks
    if group_id == "wrong_group":
        with pytest.raises(BadGroupIdException) as exc:
            response = await sse_subscribe_wallet(
                request=request,
                background_tasks=background_tasks,
                wallet_id="test_wallet_id",
                look_back=0,
                group_id=group_id,
                sse_manager=sse_manager_mock,
            )

        # Exception assertions:
        assert exc.value.status_code == 404
    else:
        response = await sse_subscribe_wallet(
            request=request,
            background_tasks=background_tasks,
            wallet_id="test_wallet_id",
            look_back=0,
            group_id=group_id,
            sse_manager=sse_manager_mock,
        )

        # Assertions
        assert isinstance(response, EventSourceResponse)
        assert response.status_code == 200


@pytest.mark.anyio
@pytest.mark.parametrize("group_id", [None, "correct_group", "wrong_group"])
async def test_sse_subscribe_wallet_topic(
    sse_manager_mock,  # pylint: disable=redefined-outer-name
    group_id,
):
    if group_id == "wrong_group":
        sse_manager_mock.check_wallet_belongs_to_group.return_value = False
    else:
        sse_manager_mock.check_wallet_belongs_to_group.return_value = True

    # Prepare the Request and BackgroundTasks objects
    request = Request(scope={"type": "http"})
    background_tasks = BackgroundTasks()

    # Call the sse_subscribe_wallet_topic function with the mocked request and background tasks
    if group_id == "wrong_group":
        with pytest.raises(BadGroupIdException) as exc:
            response = await sse_subscribe_wallet_topic(
                request=request,
                background_tasks=background_tasks,
                wallet_id="test_wallet_id",
                topic="some_topic",
                look_back=0,
                group_id=group_id,
                sse_manager=sse_manager_mock,
            )

        # Exception assertions:
        assert exc.value.status_code == 404
    else:
        response = await sse_subscribe_wallet_topic(
            request=request,
            background_tasks=background_tasks,
            wallet_id="test_wallet_id",
            topic="some_topic",
            look_back=0,
            group_id=group_id,
            sse_manager=sse_manager_mock,
        )

        # Assertions
        assert isinstance(response, EventSourceResponse)
        assert response.status_code == 200


@pytest.mark.anyio
@pytest.mark.parametrize("group_id", [None, "correct_group", "wrong_group"])
async def test_sse_subscribe_event_with_state(
    sse_manager_mock,  # pylint: disable=redefined-outer-name
    group_id,
):
    if group_id == "wrong_group":
        sse_manager_mock.check_wallet_belongs_to_group.return_value = False
    else:
        sse_manager_mock.check_wallet_belongs_to_group.return_value = True

    # Prepare the Request and BackgroundTasks objects
    request = Request(scope={"type": "http"})
    background_tasks = BackgroundTasks()

    # Call the sse_subscribe_event_with_state function with the mocked request and background tasks
    if group_id == "wrong_group":
        with pytest.raises(BadGroupIdException) as exc:
            response = await sse_subscribe_event_with_state(
                request=request,
                background_tasks=background_tasks,
                wallet_id="test_wallet_id",
                topic="some_topic",
                desired_state="some_state",
                look_back=0,
                group_id=group_id,
                sse_manager=sse_manager_mock,
            )

        # Exception assertions:
        assert exc.value.status_code == 404
    else:
        response = await sse_subscribe_event_with_state(
            request=request,
            background_tasks=background_tasks,
            wallet_id="test_wallet_id",
            topic="some_topic",
            desired_state="some_state",
            look_back=0,
            group_id=group_id,
            sse_manager=sse_manager_mock,
        )

        # Assertions
        assert isinstance(response, EventSourceResponse)
        assert response.status_code == 200


@pytest.mark.anyio
@pytest.mark.parametrize("group_id", [None, "correct_group", "wrong_group"])
async def test_sse_subscribe_stream_with_fields(
    sse_manager_mock,  # pylint: disable=redefined-outer-name
    group_id,
):
    if group_id == "wrong_group":
        sse_manager_mock.check_wallet_belongs_to_group.return_value = False
    else:
        sse_manager_mock.check_wallet_belongs_to_group.return_value = True

    # Prepare the Request and BackgroundTasks objects
    request = Request(scope={"type": "http"})
    background_tasks = BackgroundTasks()

    # Call the sse_subscribe_stream_with_fields function with the mocked request and background tasks
    if group_id == "wrong_group":
        with pytest.raises(BadGroupIdException) as exc:
            response = await sse_subscribe_stream_with_fields(
                request=request,
                background_tasks=background_tasks,
                wallet_id="test_wallet_id",
                topic="some_topic",
                field="some_field",
                field_id="some_field_id",
                look_back=0,
                group_id=group_id,
                sse_manager=sse_manager_mock,
            )

        # Exception assertions:
        assert exc.value.status_code == 404
    else:
        response = await sse_subscribe_stream_with_fields(
            request=request,
            background_tasks=background_tasks,
            wallet_id="test_wallet_id",
            topic="some_topic",
            field="some_field",
            field_id="some_field_id",
            look_back=0,
            group_id=group_id,
            sse_manager=sse_manager_mock,
        )

        # Assertions
        assert isinstance(response, EventSourceResponse)
        assert response.status_code == 200


@pytest.mark.anyio
@pytest.mark.parametrize("group_id", [None, "correct_group", "wrong_group"])
async def test_sse_subscribe_event_with_field_and_state(
    sse_manager_mock,  # pylint: disable=redefined-outer-name
    group_id,
):
    if group_id == "wrong_group":
        sse_manager_mock.check_wallet_belongs_to_group.return_value = False
    else:
        sse_manager_mock.check_wallet_belongs_to_group.return_value = True

    # Prepare the Request and BackgroundTasks objects
    request = Request(scope={"type": "http"})
    background_tasks = BackgroundTasks()

    # Call the sse_subscribe_event_with_field_and_state function with the mocked request and background tasks
    if group_id == "wrong_group":
        with pytest.raises(BadGroupIdException) as exc:
            response = await sse_subscribe_event_with_field_and_state(
                request=request,
                background_tasks=background_tasks,
                wallet_id="test_wallet_id",
                topic="some_topic",
                field="some_field",
                field_id="some_field_id",
                desired_state="some_state",
                look_back=0,
                group_id=group_id,
                sse_manager=sse_manager_mock,
            )

        # Exception assertions:
        assert exc.value.status_code == 404
    else:
        response = await sse_subscribe_event_with_field_and_state(
            request=request,
            background_tasks=background_tasks,
            wallet_id="test_wallet_id",
            topic="some_topic",
            field="some_field",
            field_id="some_field_id",
            desired_state="some_state",
            look_back=0,
            group_id=group_id,
            sse_manager=sse_manager_mock,
        )

        # Assertions
        assert isinstance(response, EventSourceResponse)
        assert response.status_code == 200
