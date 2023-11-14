import asyncio
import time
from datetime import datetime, timedelta
from itertools import chain, repeat
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.constants import MAX_EVENT_AGE_SECONDS
from shared.models.webhook_topics.base import CloudApiWebhookEventGeneric
from webhooks.dependencies.sse_manager import SseManager, _copy_queue

# pylint: disable=protected-access
# because we are testing protected methods

wallet = "wallet1"
topic = "topic1"
test_event = CloudApiWebhookEventGeneric(
    wallet_id=wallet, topic=topic, origin="multitenant", payload={"some": "data"}
)


@pytest.fixture
def redis_service_mock():
    # Setup RedisService mock
    redis_service = MagicMock()
    redis_service.redis.pubsub.return_value = AsyncMock()
    redis_service.get_events_by_timestamp = AsyncMock(return_value=[MagicMock()])
    return redis_service


@pytest.fixture
async def sse_manager(redis_service_mock):  # pylint: disable=redefined-outer-name
    # Patch to prevent background tasks from starting automatically on init
    with patch.object(SseManager, "_start_background_tasks", return_value=None):
        return SseManager(redis_service_mock)


@pytest.mark.anyio
async def test_listen_for_new_events(
    sse_manager, redis_service_mock  # pylint: disable=redefined-outer-name
):
    # Configure specific mocks for this test
    pubsub_mock = redis_service_mock.redis.pubsub.return_value
    pubsub_mock.subscribe = AsyncMock()
    pubsub_mock.get_message = AsyncMock(
        side_effect=chain(
            [{"data": b"wallet1:123456789"}],  # First message
            repeat(None),  # Keep returning None indefinitely
        )
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
    redis_service_mock.get_events_by_timestamp.assert_called_once()
    # Check if the event was added to the incoming_events queue
    assert not sse_manager.incoming_events.empty()


@pytest.mark.anyio
async def test_backfill_events(
    sse_manager, redis_service_mock  # pylint: disable=redefined-outer-name
):
    # Configure the mock for get_all_wallet_ids and get_events_by_timestamp
    redis_service_mock.get_all_wallet_ids = AsyncMock(
        return_value=["wallet1", "wallet2"]
    )
    mock_event = MagicMock()  # Mocked event object
    redis_service_mock.get_events_by_timestamp = AsyncMock(return_value=[mock_event])

    # Call the _backfill_events method
    await sse_manager._backfill_events()

    # Assertions to check if the events are fetched and added to the queue correctly
    assert redis_service_mock.get_all_wallet_ids.call_count == 1
    assert (
        redis_service_mock.get_events_by_timestamp.call_count == 2
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
    assert not sse_manager.fifo_cache["wallet1"]["topic1"].empty()
    assert not sse_manager.lifo_cache["wallet1"]["topic1"].empty()


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
