import asyncio
from unittest.mock import ANY, AsyncMock, patch

import pytest
from fastapi import BackgroundTasks, Request
from sse_starlette import EventSourceResponse

from shared.constants import DISCONNECT_CHECK_PERIOD, SSE_TIMEOUT
from shared.models.webhook_events.payloads import CloudApiWebhookEventGeneric
from waypoint.routes.sse import (
    check_disconnect,
    nats_event_stream_generator,
    sse_wait_for_event_with_field_and_state,
)
from waypoint.services.nats_service import NatsEventsProcessor
from waypoint.util.event_generator_wrapper import EventGeneratorWrapper

wallet_id = "wallet123"
topic = "some_topic"
field = "some_field"
field_id = "some_field_id"
desired_state = "some_state"
group_id = "some_group"

dummy_cloudapi_event = CloudApiWebhookEventGeneric(
    wallet_id=wallet_id,
    group_id=group_id,
    topic=topic,
    origin="xyz",
    payload={
        "dummy": "data",
        field: "some_other_field_id",
        "state": "some_other_state",
    },
)


@pytest.fixture
def nats_processor_mock():
    mock = AsyncMock(spec=NatsEventsProcessor)
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
    request = AsyncMock(spec=Request)
    request.is_disconnected.return_value = True

    stop_event = asyncio.Event()

    task = asyncio.create_task(check_disconnect(request, stop_event))
    # Give it enough time to check for disconnection and set the stop event
    await asyncio.sleep(DISCONNECT_CHECK_PERIOD * 4)

    assert stop_event.is_set()  # Expect stop_event to be set upon disconnection
    assert task.done() is True


@pytest.mark.anyio
async def test_sse_event_stream_generator_wallet_id_topic_field_desired_state(
    async_generator_mock,  # pylint: disable=redefined-outer-name
    nats_processor_mock,  # pylint: disable=redefined-outer-name
    request_mock,  # pylint: disable=redefined-outer-name
):
    expected_cloudapi_event = CloudApiWebhookEventGeneric(
        wallet_id=wallet_id,
        topic=topic,
        origin="xyz",
        group_id=group_id,
        payload={"dummy": "data", field: field_id, "state": desired_state},
    )

    # Configure the nats_processor mock
    nats_processor_mock.process_events.return_value = EventGeneratorWrapper(
        generator=async_generator_mock([dummy_cloudapi_event, expected_cloudapi_event]),
    )

    # Call the method under test
    async for event in nats_event_stream_generator(
        request=request_mock,
        background_tasks=BackgroundTasks(),
        wallet_id=wallet_id,
        topic=topic,
        field=field,
        field_id=field_id,
        desired_state=desired_state,
        group_id=group_id,
        nats_processor=nats_processor_mock,
    ):
        assert event == expected_cloudapi_event.model_dump_json()

    # Assertions
    nats_processor_mock.process_events.assert_awaited_with(
        wallet_id=wallet_id,
        topic=topic,
        group_id=group_id,
        stop_event=ANY,
        duration=SSE_TIMEOUT,
    )


@pytest.mark.anyio
async def test_sse_event_stream_generator_disconnects(
    async_generator_mock,  # pylint: disable=redefined-outer-name
    nats_processor_mock,  # pylint: disable=redefined-outer-name
):
    request = AsyncMock(spec=Request)
    request.is_disconnected.return_value = True

    expected_cloudapi_event = CloudApiWebhookEventGeneric(
        wallet_id=wallet_id,
        topic=topic,
        origin="xyz",
        group_id=group_id,
        payload={"dummy": "data", field: field_id, "state": desired_state},
    )
    # Configure the nats_processor mock
    nats_processor_mock.process_events.return_value = EventGeneratorWrapper(
        generator=async_generator_mock([dummy_cloudapi_event, expected_cloudapi_event]),
    )

    async for _ in nats_event_stream_generator(
        request=request,
        background_tasks=BackgroundTasks(),
        wallet_id=wallet_id,
        topic=topic,
        field=field,
        field_id=field_id,
        desired_state=desired_state,
        group_id=group_id,
        nats_processor=nats_processor_mock,
    ):
        pass

    assert request.is_disconnected.called
    assert await nats_processor_mock.process_events.stop_event.is_set()


@pytest.mark.anyio
async def test_nats_event_stream_generator_cancelled_error_handling(
    nats_processor_mock,  # pylint: disable=redefined-outer-name
    request_mock,  # pylint: disable=redefined-outer-name
):
    """
    Test to ensure `nats_event_stream_generator` handles asyncio.CancelledError properly.
    """
    background_tasks = BackgroundTasks()

    async def mock_event_generator():
        raise asyncio.CancelledError
        yield  # Make this function an asynchronous generator

    mock_event_generator_wrapper = AsyncMock(spec=EventGeneratorWrapper)
    mock_event_generator_wrapper.__aenter__.return_value = mock_event_generator()
    mock_event_generator_wrapper.__aexit__.return_value = None

    nats_processor_mock.process_events.return_value = mock_event_generator_wrapper

    generator = nats_event_stream_generator(
        request=request_mock,
        background_tasks=background_tasks,
        wallet_id="wallet123",
        topic="some_topic",
        field="some_field",
        field_id="some_field_id",
        desired_state="some_state",
        group_id="some_group",
        nats_processor=nats_processor_mock,
    )

    async for _ in generator:
            pass

    # Assert that stop_event is set when asyncio.CancelledError is raised
    assert await nats_processor_mock.process_events.stop_event.is_set()
    request_mock.is_disconnected.assert_not_called()

@pytest.mark.anyio
async def test_sse_event_stream(
    async_generator_mock,  # pylint: disable=redefined-outer-name
    nats_processor_mock,  # pylint: disable=redefined-outer-name
    request_mock,  # pylint: disable=redefined-outer-name
):
    expected_cloudapi_event = CloudApiWebhookEventGeneric(
        wallet_id=wallet_id,
        topic=topic,
        origin="xyz",
        group_id=group_id,
        payload={"dummy": "data", field: field_id, "state": desired_state},
    )

    # Configure the nats_processor mock
    nats_processor_mock.process_events.return_value = EventGeneratorWrapper(
        generator=async_generator_mock([dummy_cloudapi_event, expected_cloudapi_event]),
    )

    with patch(
        "waypoint.routes.sse.nats_event_stream_generator"
    ) as nats_event_stream_generator_mock:
        nats_event_stream_generator_mock.return_value = async_generator_mock(
            [expected_cloudapi_event]
        )

        event_stream = await sse_wait_for_event_with_field_and_state(
            request=request_mock,
            background_tasks=BackgroundTasks(),
            wallet_id=wallet_id,
            topic=topic,
            field=field,
            field_id=field_id,
            desired_state=desired_state,
            group_id=group_id,
            nats_processor=nats_processor_mock,
        )

        assert isinstance(event_stream, EventSourceResponse)
        assert event_stream.status_code == 200

        nats_event_stream_generator_mock.assert_called_once_with(
            request=request_mock,
            background_tasks=ANY,
            wallet_id=wallet_id,
            topic=topic,
            field=field,
            field_id=field_id,
            desired_state=desired_state,
            group_id=group_id,
            nats_processor=nats_processor_mock,
        )
