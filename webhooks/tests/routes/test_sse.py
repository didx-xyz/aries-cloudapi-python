from unittest.mock import AsyncMock

import pytest
from fastapi import BackgroundTasks, Request
from sse_starlette import EventSourceResponse

from webhooks.services.sse_manager import SseManager
from webhooks.web.routers.sse import (
    BadGroupIdException,
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
