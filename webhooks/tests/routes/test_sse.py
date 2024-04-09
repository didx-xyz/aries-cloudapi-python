import asyncio
from unittest.mock import ANY, AsyncMock, Mock, patch

import pytest
from fastapi import BackgroundTasks, Request
from sse_starlette import EventSourceResponse

from shared.constants import DISCONNECT_CHECK_PERIOD, MAX_EVENT_AGE_SECONDS, SSE_TIMEOUT
from shared.models.webhook_events import WEBHOOK_TOPIC_ALL
from shared.models.webhook_events.payloads import CloudApiWebhookEventGeneric
from webhooks.services.sse_manager import SseManager
from webhooks.util.event_generator_wrapper import EventGeneratorWrapper
from webhooks.web.routers.sse import (
    BadGroupIdException,
    check_disconnection,
    sse_event_stream_generator,
    sse_subscribe_event_with_field_and_state,
    sse_subscribe_event_with_state,
    sse_subscribe_stream_with_fields,
    sse_subscribe_wallet,
    sse_subscribe_wallet_topic,
)

wallet_id = "wallet123"
topic = "some_topic"
field = "some_field"
field_id = "some_field_id"
desired_state = "some_state"

dummy_cloudapi_event = CloudApiWebhookEventGeneric(
    wallet_id=wallet_id,
    topic=topic,
    origin="xyz",
    group_id="some_group",
    payload={"dummy": "data"},
)


@pytest.fixture
def sse_manager_mock():
    mock = AsyncMock(spec=SseManager)
    return mock


@pytest.fixture
def request_mock():
    mock_request = AsyncMock(spec=Request)
    mock_request.is_disconnected.return_value = False
    return mock_request


@pytest.fixture
def async_generator_mock():
    async def _mock_gen(*args):
        for value in args[0]:
            yield value

    return _mock_gen


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
async def test_sse_event_stream_generator_wallet_id(
    async_generator_mock,  # pylint: disable=redefined-outer-name
    sse_manager_mock,  # pylint: disable=redefined-outer-name
    request_mock,  # pylint: disable=redefined-outer-name
):
    # Configure the sse_manager mock
    sse_manager_mock.sse_event_stream.return_value = EventGeneratorWrapper(
        generator=async_generator_mock([dummy_cloudapi_event]),
        populate_task=Mock(),
    )

    # Call the method under test
    async for event in sse_event_stream_generator(
        sse_manager=sse_manager_mock,
        request=request_mock,
        background_tasks=BackgroundTasks(),
        wallet_id=wallet_id,
        logger=Mock(),
    ):
        assert event == dummy_cloudapi_event.model_dump_json()

    # Assertions
    sse_manager_mock.sse_event_stream.assert_awaited_with(
        wallet=wallet_id,
        topic=WEBHOOK_TOPIC_ALL,
        look_back=MAX_EVENT_AGE_SECONDS,
        stop_event=ANY,
        duration=0,
    )


@pytest.mark.anyio
async def test_sse_event_stream_generator_wallet_id_disconnect(
    async_generator_mock,  # pylint: disable=redefined-outer-name
    sse_manager_mock,  # pylint: disable=redefined-outer-name
    request_mock,  # pylint: disable=redefined-outer-name
):
    request_mock.is_disconnected.return_value = AsyncMock(True)

    # Configure the sse_manager mock
    sse_manager_mock.sse_event_stream.return_value = EventGeneratorWrapper(
        generator=async_generator_mock([dummy_cloudapi_event]),
        populate_task=Mock(),
    )

    background_tasks = BackgroundTasks()

    # Convert generator to a list to force evaluation
    events = [
        event
        async for event in sse_event_stream_generator(
            sse_manager=sse_manager_mock,
            request=request_mock,
            background_tasks=background_tasks,
            wallet_id=wallet_id,
            logger=Mock(),
        )
    ]

    # Assertions
    assert len(events) == 0, "Expected no events to be yielded after disconnection."
    request_mock.is_disconnected.assert_awaited()
    assert (
        len(background_tasks.tasks) > 0
    ), "Expected at least one background task for disconnection check."


@pytest.mark.anyio
async def test_sse_event_stream_generator_wallet_id_topic(
    async_generator_mock,  # pylint: disable=redefined-outer-name
    sse_manager_mock,  # pylint: disable=redefined-outer-name
    request_mock,  # pylint: disable=redefined-outer-name
):
    # Configure the sse_manager mock
    sse_manager_mock.sse_event_stream.return_value = EventGeneratorWrapper(
        generator=async_generator_mock([dummy_cloudapi_event]),
        populate_task=Mock(),
    )

    # Call the method under test
    async for event in sse_event_stream_generator(
        sse_manager=sse_manager_mock,
        request=request_mock,
        background_tasks=BackgroundTasks(),
        wallet_id=wallet_id,
        topic=topic,
        logger=Mock(),
    ):
        assert event == dummy_cloudapi_event.model_dump_json()

    # Assertions
    sse_manager_mock.sse_event_stream.assert_awaited_with(
        wallet=wallet_id,
        topic=topic,
        look_back=MAX_EVENT_AGE_SECONDS,
        stop_event=ANY,
        duration=0,
    )


@pytest.mark.anyio
async def test_sse_event_stream_generator_wallet_id_topic_desired_state(
    async_generator_mock,  # pylint: disable=redefined-outer-name
    sse_manager_mock,  # pylint: disable=redefined-outer-name
    request_mock,  # pylint: disable=redefined-outer-name
):
    expected_cloudapi_event = CloudApiWebhookEventGeneric(
        wallet_id=wallet_id,
        topic=topic,
        origin="xyz",
        group_id="some_group",
        payload={"dummy": "data", "state": desired_state},
    )
    # Configure the sse_manager mock
    sse_manager_mock.sse_event_stream.return_value = EventGeneratorWrapper(
        generator=async_generator_mock([dummy_cloudapi_event, expected_cloudapi_event]),
        populate_task=Mock(),
    )

    # Call the method under test
    async for event in sse_event_stream_generator(
        sse_manager=sse_manager_mock,
        request=request_mock,
        background_tasks=BackgroundTasks(),
        wallet_id=wallet_id,
        topic=topic,
        desired_state=desired_state,
        logger=Mock(),
    ):
        assert event == expected_cloudapi_event.model_dump_json()

    # Assertions
    sse_manager_mock.sse_event_stream.assert_awaited_with(
        wallet=wallet_id,
        topic=topic,
        look_back=MAX_EVENT_AGE_SECONDS,
        stop_event=ANY,
        duration=SSE_TIMEOUT,
    )


@pytest.mark.anyio
async def test_sse_event_stream_generator_wallet_id_topic_field(
    async_generator_mock,  # pylint: disable=redefined-outer-name
    sse_manager_mock,  # pylint: disable=redefined-outer-name
    request_mock,  # pylint: disable=redefined-outer-name
):
    expected_cloudapi_event = CloudApiWebhookEventGeneric(
        wallet_id=wallet_id,
        topic=topic,
        origin="xyz",
        group_id="some_group",
        payload={"dummy": "data", field: field_id},
    )

    # Configure the sse_manager mock
    sse_manager_mock.sse_event_stream.return_value = EventGeneratorWrapper(
        generator=async_generator_mock([dummy_cloudapi_event, expected_cloudapi_event]),
        populate_task=Mock(),
    )

    # Call the method under test
    async for event in sse_event_stream_generator(
        sse_manager=sse_manager_mock,
        request=request_mock,
        background_tasks=BackgroundTasks(),
        wallet_id=wallet_id,
        topic=topic,
        field=field,
        field_id=field_id,
        logger=Mock(),
    ):
        assert event == expected_cloudapi_event.model_dump_json()

    # Assertions
    sse_manager_mock.sse_event_stream.assert_awaited_with(
        wallet=wallet_id,
        topic=topic,
        look_back=MAX_EVENT_AGE_SECONDS,
        stop_event=ANY,
        duration=0,
    )


@pytest.mark.anyio
async def test_sse_event_stream_generator_wallet_id_topic_field_desired_state(
    async_generator_mock,  # pylint: disable=redefined-outer-name
    sse_manager_mock,  # pylint: disable=redefined-outer-name
    request_mock,  # pylint: disable=redefined-outer-name
):
    expected_cloudapi_event = CloudApiWebhookEventGeneric(
        wallet_id=wallet_id,
        topic=topic,
        origin="xyz",
        group_id="some_group",
        payload={"dummy": "data", field: field_id, "state": desired_state},
    )

    # Configure the sse_manager mock
    sse_manager_mock.sse_event_stream.return_value = EventGeneratorWrapper(
        generator=async_generator_mock([dummy_cloudapi_event, expected_cloudapi_event]),
        populate_task=Mock(),
    )

    # Call the method under test
    async for event in sse_event_stream_generator(
        sse_manager=sse_manager_mock,
        request=request_mock,
        background_tasks=BackgroundTasks(),
        wallet_id=wallet_id,
        topic=topic,
        field=field,
        field_id=field_id,
        desired_state=desired_state,
        logger=Mock(),
    ):
        assert event == expected_cloudapi_event.model_dump_json()

    # Assertions
    sse_manager_mock.sse_event_stream.assert_awaited_with(
        wallet=wallet_id,
        topic=topic,
        look_back=MAX_EVENT_AGE_SECONDS,
        stop_event=ANY,
        duration=SSE_TIMEOUT,
    )


@pytest.mark.anyio
@pytest.mark.parametrize("group_id", [None, "correct_group", "wrong_group"])
@pytest.mark.parametrize("look_back", [0.0, 15.0])
async def test_sse_subscribe_wallet(
    sse_manager_mock,  # pylint: disable=redefined-outer-name
    group_id,
    look_back,
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
                wallet_id=wallet_id,
                look_back=look_back,
                group_id=group_id,
                sse_manager=sse_manager_mock,
            )

        # Exception assertions:
        assert exc.value.status_code == 404
    else:
        with patch(
            "webhooks.web.routers.sse.sse_event_stream_generator"
        ) as event_stream_generator:
            response = await sse_subscribe_wallet(
                request=request,
                background_tasks=background_tasks,
                wallet_id=wallet_id,
                look_back=look_back,
                group_id=group_id,
                sse_manager=sse_manager_mock,
            )

            # Assertions
            assert isinstance(response, EventSourceResponse)
            assert response.status_code == 200

            event_stream_generator.assert_called_once_with(
                sse_manager=sse_manager_mock,
                request=request,
                background_tasks=background_tasks,
                wallet_id=wallet_id,
                look_back=look_back,
                logger=ANY,
            )


@pytest.mark.anyio
@pytest.mark.parametrize("group_id", [None, "correct_group", "wrong_group"])
@pytest.mark.parametrize("look_back", [0.0, 15.0])
async def test_sse_subscribe_wallet_topic(
    sse_manager_mock,  # pylint: disable=redefined-outer-name
    group_id,
    look_back,
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
                wallet_id=wallet_id,
                topic=topic,
                look_back=look_back,
                group_id=group_id,
                sse_manager=sse_manager_mock,
            )

        # Exception assertions:
        assert exc.value.status_code == 404
    else:
        with patch(
            "webhooks.web.routers.sse.sse_event_stream_generator"
        ) as event_stream_generator:
            response = await sse_subscribe_wallet_topic(
                request=request,
                background_tasks=background_tasks,
                wallet_id=wallet_id,
                topic=topic,
                look_back=look_back,
                group_id=group_id,
                sse_manager=sse_manager_mock,
            )

            # Assertions
            assert isinstance(response, EventSourceResponse)
            assert response.status_code == 200

            event_stream_generator.assert_called_once_with(
                sse_manager=sse_manager_mock,
                request=request,
                background_tasks=background_tasks,
                wallet_id=wallet_id,
                topic=topic,
                look_back=look_back,
                logger=ANY,
            )


@pytest.mark.anyio
@pytest.mark.parametrize("group_id", [None, "correct_group", "wrong_group"])
@pytest.mark.parametrize("look_back", [0.0, 15.0])
async def test_sse_subscribe_event_with_state(
    sse_manager_mock,  # pylint: disable=redefined-outer-name
    group_id,
    look_back,
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
                wallet_id=wallet_id,
                topic=topic,
                desired_state=desired_state,
                look_back=look_back,
                group_id=group_id,
                sse_manager=sse_manager_mock,
            )

        # Exception assertions:
        assert exc.value.status_code == 404
    else:
        with patch(
            "webhooks.web.routers.sse.sse_event_stream_generator"
        ) as event_stream_generator:
            response = await sse_subscribe_event_with_state(
                request=request,
                background_tasks=background_tasks,
                wallet_id=wallet_id,
                topic=topic,
                desired_state=desired_state,
                look_back=look_back,
                group_id=group_id,
                sse_manager=sse_manager_mock,
            )

            # Assertions
            assert isinstance(response, EventSourceResponse)
            assert response.status_code == 200

            event_stream_generator.assert_called_once_with(
                sse_manager=sse_manager_mock,
                request=request,
                background_tasks=background_tasks,
                wallet_id=wallet_id,
                topic=topic,
                desired_state=desired_state,
                look_back=look_back,
                logger=ANY,
            )


@pytest.mark.anyio
@pytest.mark.parametrize("group_id", [None, "correct_group", "wrong_group"])
@pytest.mark.parametrize("look_back", [0.0, 15.0])
async def test_sse_subscribe_stream_with_fields(
    sse_manager_mock,  # pylint: disable=redefined-outer-name
    group_id,
    look_back,
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
                wallet_id=wallet_id,
                topic=topic,
                field=field,
                field_id=field_id,
                look_back=look_back,
                group_id=group_id,
                sse_manager=sse_manager_mock,
            )

        # Exception assertions:
        assert exc.value.status_code == 404
    else:
        with patch(
            "webhooks.web.routers.sse.sse_event_stream_generator"
        ) as event_stream_generator:
            response = await sse_subscribe_stream_with_fields(
                request=request,
                background_tasks=background_tasks,
                wallet_id=wallet_id,
                topic=topic,
                field=field,
                field_id=field_id,
                look_back=look_back,
                group_id=group_id,
                sse_manager=sse_manager_mock,
            )

            # Assertions
            assert isinstance(response, EventSourceResponse)
            assert response.status_code == 200

            event_stream_generator.assert_called_once_with(
                sse_manager=sse_manager_mock,
                request=request,
                background_tasks=background_tasks,
                wallet_id=wallet_id,
                topic=topic,
                field=field,
                field_id=field_id,
                look_back=look_back,
                logger=ANY,
            )


@pytest.mark.anyio
@pytest.mark.parametrize("group_id", [None, "correct_group", "wrong_group"])
@pytest.mark.parametrize("look_back", [0.0, 15.0])
async def test_sse_subscribe_event_with_field_and_state(
    sse_manager_mock,  # pylint: disable=redefined-outer-name
    group_id,
    look_back,
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
                wallet_id=wallet_id,
                topic=topic,
                field=field,
                field_id=field_id,
                desired_state=desired_state,
                look_back=look_back,
                group_id=group_id,
                sse_manager=sse_manager_mock,
            )

        # Exception assertions:
        assert exc.value.status_code == 404
    else:
        with patch(
            "webhooks.web.routers.sse.sse_event_stream_generator"
        ) as event_stream_generator:
            response = await sse_subscribe_event_with_field_and_state(
                request=request,
                background_tasks=background_tasks,
                wallet_id=wallet_id,
                topic=topic,
                field=field,
                field_id=field_id,
                desired_state=desired_state,
                look_back=look_back,
                group_id=group_id,
                sse_manager=sse_manager_mock,
            )

            # Assertions
            assert isinstance(response, EventSourceResponse)
            assert response.status_code == 200

            event_stream_generator.assert_called_once_with(
                sse_manager=sse_manager_mock,
                request=request,
                background_tasks=background_tasks,
                wallet_id=wallet_id,
                topic=topic,
                field=field,
                field_id=field_id,
                desired_state=desired_state,
                look_back=look_back,
                logger=ANY,
            )
