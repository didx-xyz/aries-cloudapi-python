import asyncio
import time
from datetime import datetime, timedelta
from itertools import chain, repeat
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from shared.constants import MAX_EVENT_AGE_SECONDS
from shared.models.webhook_events.payloads import CloudApiWebhookEventGeneric
from webhooks.services.sse_manager import SseManager, _copy_queue

# pylint: disable=protected-access
# because we are testing protected methods

wallet = "wallet1"
topic = "topic1"
test_event = CloudApiWebhookEventGeneric(
    wallet_id=wallet, topic=topic, origin="multitenant", payload={"some": "data"}
)


@pytest.fixture
def redis_service_mock():
    # Setup WebhooksRedisService mock
    redis_service = MagicMock()
    redis_service.redis.pubsub.return_value = Mock()
    redis_service.get_json_cloudapi_events_by_timestamp = Mock(
        return_value=[MagicMock()]
    )
    return redis_service


@pytest.fixture
def sse_manager(redis_service_mock):  # pylint: disable=redefined-outer-name
    # Patch to prevent background tasks from starting automatically on init
    return SseManager(redis_service_mock)


@pytest.mark.anyio
async def test_start(sse_manager):  # pylint: disable=redefined-outer-name
    # Mock the coroutine methods
    sse_manager._backfill_events = AsyncMock()
    sse_manager._listen_for_new_events = AsyncMock()
    sse_manager._process_incoming_events = AsyncMock()
    sse_manager._cleanup_cache = AsyncMock()

    sse_manager.start()

    # Ensure background tasks are started
    assert len(sse_manager._tasks) == 3  # correct num tasks stored

    sse_manager._pubsub = True
    assert sse_manager.are_tasks_running()


@pytest.mark.anyio
async def test_stop(sse_manager):  # pylint: disable=redefined-outer-name
    # Setup a dummy task to simulate an ongoing task
    dummy_task1 = asyncio.create_task(asyncio.sleep(1))
    dummy_task2 = asyncio.create_task(asyncio.sleep(1))
    sse_manager._tasks.append(dummy_task1)
    sse_manager._tasks.append(dummy_task2)

    # Simulate an existing pubsub instance
    sse_manager._pubsub = Mock()

    await sse_manager.stop()

    # Check that all tasks were attempted to be cancelled
    assert dummy_task1.cancelled()
    assert dummy_task2.cancelled()

    # Ensure tasks list is cleared
    assert len(sse_manager._tasks) == 0

    # Verify that pubsub_thread stop and pubsub disconnect methods were called
    sse_manager._pubsub.disconnect.assert_called_once()


# Sample test for checking if tasks are running
@pytest.mark.anyio
async def test_are_tasks_running_x(sse_manager):  # pylint: disable=redefined-outer-name
    sse_manager._pubsub = True
    sse_manager._tasks = []
    # Since we didn't start a task, it should be considered not running
    assert not sse_manager.are_tasks_running()

    # Create dummy task and stop it
    dummy_done_task = MagicMock()
    dummy_done_task.done.return_value = True
    sse_manager._tasks = [dummy_done_task]

    # Task has been cancelled, it should be considered not running
    assert not sse_manager.are_tasks_running()

    # Now reset task to appear as still running, to test pubsub case
    dummy_done_task.done.return_value = False
    sse_manager._tasks = [dummy_done_task]
    assert sse_manager.are_tasks_running()  # is running again

    # when pubsub stops, tasks should be not running
    sse_manager._pubsub = None
    assert not sse_manager.are_tasks_running()


@pytest.mark.anyio
@patch(
    "shared.models.webhook_events.payloads.CloudApiWebhookEventGeneric.model_validate_json"
)
async def test_listen_for_new_events(
    mock_model_validate_json,
    sse_manager,  # pylint: disable=redefined-outer-name
    redis_service_mock,  # pylint: disable=redefined-outer-name
):
    # Configure specific mocks for this test
    pubsub_mock = redis_service_mock.redis.pubsub.return_value
    pubsub_mock.subscribe = Mock()
    pubsub_mock.get_message = Mock(
        side_effect=chain(
            [{"data": b"wallet1:123456789"}],  # First message
            repeat(None),  # Keep returning None indefinitely
        )
    )

    # Mock for CloudApiWebhookEventGeneric.model_validate_json
    mock_model_validate_json.return_value = CloudApiWebhookEventGeneric(
        wallet_id="test_wallet", topic="test_topic", origin="abc", payload={}
    )

    # Use asyncio.wait_for to prevent the test from hanging indefinitely
    try:
        await asyncio.wait_for(sse_manager._listen_for_new_events(), timeout=0.5)
    except asyncio.TimeoutError:
        pass  # Timeout is expected due to the infinite loop

    # Assertions to verify that messages were received and processed
    pubsub_mock.subscribe.assert_called_once_with(
        sse_manager.redis_service.sse_event_pubsub_channel
    )
    assert pubsub_mock.get_message.call_count >= 1
    redis_service_mock.get_json_cloudapi_events_by_timestamp.assert_called_once()

    # Check if the event was added to the incoming_events queue
    assert not sse_manager.incoming_events.empty()


@pytest.mark.anyio
async def test_backfill_events(
    sse_manager, redis_service_mock  # pylint: disable=redefined-outer-name
):
    # Configure the mock for get_all_wallet_ids and get_events_by_timestamp
    redis_service_mock.get_all_cloudapi_wallet_ids = Mock(
        return_value=["wallet1", "wallet2"]
    )
    mock_event = MagicMock()  # Mocked event object
    redis_service_mock.get_cloudapi_events_by_timestamp = Mock(
        return_value=[mock_event]
    )

    # Call the _backfill_events method
    await sse_manager._backfill_events()

    # Assertions to check if the events are fetched and added to the queue correctly
    assert redis_service_mock.get_all_cloudapi_wallet_ids.call_count == 1
    assert (
        redis_service_mock.get_cloudapi_events_by_timestamp.call_count == 2
    )  # Called for each wallet
    assert sse_manager.incoming_events.qsize() == 2  # One event for each wallet


@pytest.mark.anyio
async def test_process_incoming_events(
    sse_manager,  # pylint: disable=redefined-outer-name
):
    await sse_manager.incoming_events.put(test_event)

    try:
        await asyncio.wait_for(sse_manager._process_incoming_events(), timeout=1)
    except asyncio.TimeoutError:
        pass  # Timeout is expected due to the infinite loop

    # Assertions to verify that the event is processed and added to the FIFO and LIFO caches
    assert not sse_manager.fifo_cache[wallet][topic].empty()
    assert not sse_manager.lifo_cache[wallet][topic].empty()


@pytest.mark.anyio
async def test_sse_event_stream(sse_manager):  # pylint: disable=redefined-outer-name
    stop_event = asyncio.Event()
    duration = 2  # seconds

    event_stream_wrapper = await sse_manager.sse_event_stream(
        wallet=wallet, topic=topic, stop_event=stop_event, duration=duration
    )

    # Get the client_queue from the task's context (unconventional, relies on coroutine internals)
    client_queue = event_stream_wrapper.populate_task.get_coro().cr_frame.f_locals[
        "client_queue"
    ]

    # Simulate adding an event to the client_queue
    await client_queue.put(test_event)

    async with event_stream_wrapper as event_generator:
        try:
            async for event in event_generator:
                # Assertions for the event
                assert event.wallet_id == wallet
                assert event.topic == topic
                break
        except asyncio.TimeoutError:
            pytest.fail("Timeout occurred while waiting for an event")

    # Test whether stop_event stops the generator
    stop_event.set()
    # Since the generator should be stopped, iterating it should immediately exit
    async for event in event_generator:
        pytest.fail("Event generator should have been stopped")


@pytest.mark.anyio
async def test_populate_client_queue(
    sse_manager,  # pylint: disable=redefined-outer-name
):
    client_queue = asyncio.Queue()

    # Simulate adding an event to the LIFO cache
    timestamp = time.time()
    await sse_manager.lifo_cache[wallet][topic].put((timestamp, test_event))

    # Run _populate_client_queue in a background task
    populate_task = asyncio.create_task(
        sse_manager._populate_client_queue(
            wallet=wallet, topic=topic, client_queue=client_queue
        )
    )

    # Wait for a short period to allow the background task to run
    await asyncio.sleep(0.1)

    # Stop the background task
    populate_task.cancel()
    try:
        await populate_task
    except asyncio.CancelledError:
        pass

    # Check if the event was added to the client queue
    event_in_client_queue = await client_queue.get()
    assert event_in_client_queue == test_event


@pytest.mark.anyio
async def test_append_to_queue(sse_manager):  # pylint: disable=redefined-outer-name
    client_queue = asyncio.Queue()
    event_log = []

    # Add an event to the LIFO queue
    timestamp = time.time()
    await sse_manager.lifo_cache[wallet][topic].put((timestamp, test_event))

    # Call _append_to_queue
    event_log = await sse_manager._append_to_queue(
        wallet=wallet, topic=topic, client_queue=client_queue, event_log=event_log
    )

    # Check if the event was added to the client queue and event log
    assert await client_queue.get() == test_event
    assert (timestamp, test_event) in event_log


@pytest.mark.anyio
async def test_cleanup_cache(sse_manager):  # pylint: disable=redefined-outer-name
    # Add an old event to the cache
    timestamp = time.time() - (MAX_EVENT_AGE_SECONDS + 1)
    await sse_manager.lifo_cache[wallet][topic].put((timestamp, test_event))
    sse_manager._cache_last_accessed[wallet][topic] = datetime.now() - timedelta(
        seconds=MAX_EVENT_AGE_SECONDS + 1
    )

    # Run cleanup task
    cleanup_task = asyncio.create_task(sse_manager._cleanup_cache())
    await asyncio.sleep(0.1)  # Short sleep to let the cleanup task run
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

    # Check if the cache has been cleaned
    assert topic not in sse_manager.lifo_cache[wallet]
    assert topic not in sse_manager.fifo_cache[wallet]
    assert topic not in sse_manager.cache_locks[wallet]
    assert topic not in sse_manager._cache_last_accessed[wallet]


@pytest.mark.anyio
async def test_check_wallet_belongs_to_group_immediate_success(sse_manager):
    sse_manager.redis_service.check_wallet_belongs_to_group = Mock(return_value=True)

    result = await sse_manager.check_wallet_belongs_to_group(
        wallet_id="wallet123", group_id="group456"
    )

    sse_manager.redis_service.check_wallet_belongs_to_group.assert_called_once_with(
        wallet_id="wallet123", group_id="group456"
    )
    assert result is True


@pytest.mark.anyio
async def test_check_wallet_belongs_to_group_eventual_success(sse_manager):
    side_effects = [False] * 3 + [True]  # Fails 3 times, then succeeds
    sse_manager.redis_service.check_wallet_belongs_to_group = Mock(
        side_effect=side_effects
    )

    result = await sse_manager.check_wallet_belongs_to_group(
        wallet_id="wallet123", group_id="group456", delay=0.01
    )

    assert sse_manager.redis_service.check_wallet_belongs_to_group.call_count == 4
    assert result is True


@pytest.mark.anyio
async def test_check_wallet_belongs_to_group_failure(sse_manager):
    sse_manager.redis_service.check_wallet_belongs_to_group = Mock(return_value=False)

    result = await sse_manager.check_wallet_belongs_to_group(
        wallet_id="wallet123", group_id="group456", delay=0.01
    )

    assert sse_manager.redis_service.check_wallet_belongs_to_group.call_count == 10
    assert result is False


@pytest.mark.anyio
async def test_copy_queue():
    # Create a queue with some items
    original_queue = asyncio.Queue()
    test_event2 = CloudApiWebhookEventGeneric(
        wallet_id="wallet2",
        topic="topic2",
        origin="origin2",
        payload={"data": "value2"},
    )
    timestamp1 = time.time()
    timestamp2 = time.time() - MAX_EVENT_AGE_SECONDS / 2  # Event within max age
    await original_queue.put((timestamp1, test_event))
    await original_queue.put((timestamp2, test_event2))

    # Call _copy_queue
    lifo_queue, fifo_queue = await _copy_queue(original_queue)

    # Check if the queues have been copied correctly
    assert await fifo_queue.get() == (timestamp1, test_event)
    assert await fifo_queue.get() == (timestamp2, test_event2)
    assert await lifo_queue.get() == (timestamp2, test_event2)
    assert await lifo_queue.get() == (timestamp1, test_event)

    # Check if the original queue is empty
    assert original_queue.empty()
