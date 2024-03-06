import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from redis.client import PubSubWorkerThread
from redis.cluster import ClusterPubSub

from endorser.services.endorsement_processor import EndorsementProcessor
from shared.constants import GOVERNANCE_LABEL

# pylint: disable=redefined-outer-name
# because re-using fixtures in same module
# pylint: disable=protected-access
# because we are testing protected methods


@pytest.fixture
def redis_service_mock():
    redis_service = MagicMock()
    redis_service.endorsement_redis_prefix = "endorse:"
    redis_service.scan_keys = Mock(return_value=["endorse:key1", "endorse:key2"])
    redis_service.get = Mock(side_effect=["event_json1", "event_json2"])
    return redis_service


@pytest.fixture
def endorsement_processor_mock(redis_service_mock):
    processor = EndorsementProcessor(redis_service=redis_service_mock)
    # Mock pubsub
    processor._pubsub_thread = Mock(spec=PubSubWorkerThread)
    processor._pubsub_thread.is_alive.return_value = True
    processor._pubsub = Mock(spec=ClusterPubSub)

    processor.endorse_prefix = "endorse"
    return processor


@pytest.mark.anyio
async def test_start_and_tasks_are_running(endorsement_processor_mock):
    endorsement_processor_mock._process_endorsement_requests = AsyncMock()

    endorsement_processor_mock.start()
    # Ensure background tasks are started
    assert len(endorsement_processor_mock._tasks) > 0
    assert endorsement_processor_mock.are_tasks_running()


@pytest.mark.anyio
async def test_stop(endorsement_processor_mock):
    # Setup a dummy task to simulate an ongoing task
    dummy_task = asyncio.create_task(asyncio.sleep(1))
    endorsement_processor_mock._tasks.append(dummy_task)

    # Simulate an existing pubsub_thread and pubsub instance
    # endorsement_processor_mock._pubsub_thread = Mock(spec=PubSubWorkerThread)
    endorsement_processor_mock._pubsub = Mock()

    await endorsement_processor_mock.stop()

    # Check that all tasks were attempted to be cancelled
    assert dummy_task.cancelled()

    # Ensure tasks list is cleared
    assert len(endorsement_processor_mock._tasks) == 0

    # Verify that pubsub_thread stop and pubsub disconnect methods were called
    endorsement_processor_mock._pubsub_thread.stop.assert_called_once()
    endorsement_processor_mock._pubsub.disconnect.assert_called_once()


# Sample test for checking if tasks are running
@pytest.mark.anyio
async def test_are_tasks_running_x(endorsement_processor_mock):
    endorsement_processor_mock._tasks = []
    # Since we didn't start a task, it should be considered not running
    assert not endorsement_processor_mock.are_tasks_running()

    # Create dummy task and stop it
    dummy_done_task = MagicMock()
    dummy_done_task.done.return_value = True
    endorsement_processor_mock._tasks = [dummy_done_task]

    # Task has been cancelled, it should be considered not running
    assert not endorsement_processor_mock.are_tasks_running()

    # Now reset task to appear as still running, to test pubsub thread case
    dummy_done_task.done.return_value = False
    endorsement_processor_mock._tasks = [dummy_done_task]
    # when pubsub thread stops, tasks should be not running
    endorsement_processor_mock._pubsub_thread.is_alive.return_value = False
    assert not endorsement_processor_mock.are_tasks_running()


@pytest.mark.anyio
async def test_set_notification_handler(endorsement_processor_mock):
    # Mock the Redis message to simulate a keyspace notification
    mock_msg = {
        "type": "pmessage",
        "pattern": None,
        "channel": b"__keyevent@0__:set",
        "data": b"endorse:sample_key",
    }

    # Mock the _new_event_notification event inside the processor
    endorsement_processor_mock._new_event_notification = Mock()

    # Call the method with the mocked message
    endorsement_processor_mock._set_notification_handler(mock_msg)

    # Verify that _new_event_notification.set() was called
    endorsement_processor_mock._new_event_notification.set.assert_called_once_with()

    # Test with a non-matching message to ensure the set() method is not called
    non_matching_msg = mock_msg.copy()
    non_matching_msg["data"] = b"nonmatching:sample_key"
    endorsement_processor_mock._set_notification_handler(non_matching_msg)

    # Verify that set() method is still called only once from the first call
    endorsement_processor_mock._new_event_notification.set.assert_called_once()


def test_start_notification_listener(endorsement_processor_mock):
    endorsement_processor_mock._pubsub.psubscribe = Mock()
    endorsement_processor_mock._pubsub.run_in_thread = Mock()

    # Call the method
    endorsement_processor_mock._start_notification_listener()

    # Verify psubscribe and run_in_thread was called correctly
    endorsement_processor_mock._pubsub.psubscribe.assert_called_once()
    endorsement_processor_mock._pubsub.run_in_thread.assert_called_once()


@pytest.mark.anyio
async def test_process_endorsement_requests(endorsement_processor_mock):
    scan_results = [
        [],  # empty list to start
        ["endorse:key1"],  # Then a key returned from the scan
        ["endorse:key2", "endorse:key3"],  # Then 2 keys in a batch
        Exception(
            "Force inf loop to stop"
        ),  # force loop to exit after processing available keys
    ]
    redis_service = Mock()
    redis_service.scan_keys = Mock(side_effect=scan_results)
    endorsement_processor_mock.redis_service = redis_service

    # Store processed keys for assertion
    processed_keys = []

    # Override _attempt_process_endorsement to track keys and then set the done_event
    async def mock_attempt_process_endorsement(key):
        processed_keys.append(key)

    endorsement_processor_mock._attempt_process_endorsement = (
        mock_attempt_process_endorsement
    )

    # Exception is to force the NoReturn function to exit
    with pytest.raises(Exception):
        await endorsement_processor_mock._process_endorsement_requests()

    # Assert that the keys were processed
    assert len(processed_keys) == 3
    assert processed_keys == ["endorse:key1", "endorse:key2", "endorse:key3"]


@pytest.mark.anyio
async def test_attempt_process_endorsement(endorsement_processor_mock):
    event_key = "endorse:key"
    lock_key = f"lock:{event_key}"
    endorsement_processor_mock.redis_service.set_lock.return_value = True
    endorsement_processor_mock._process_endorsement_event = AsyncMock()

    await endorsement_processor_mock._attempt_process_endorsement(event_key)

    endorsement_processor_mock.redis_service.set_lock.assert_called_with(
        lock_key, px=500
    )
    endorsement_processor_mock.redis_service.get.assert_called_with(event_key)
    endorsement_processor_mock._process_endorsement_event.assert_called_once_with(
        "event_json1"
    )
    endorsement_processor_mock.redis_service.delete_key.assert_called_with(lock_key)


@pytest.mark.anyio
async def test_attempt_process_endorsement_x(endorsement_processor_mock):
    endorsement_processor_mock._handle_unprocessable_endorse_event = Mock()
    endorsement_processor_mock._process_endorsement_event = AsyncMock(
        side_effect=Exception("Test")
    )
    await endorsement_processor_mock._attempt_process_endorsement("key")

    # Assert _handle_unprocessable_endorse_event is called when exception was raised
    endorsement_processor_mock._handle_unprocessable_endorse_event.assert_called_once()


@pytest.mark.anyio
async def test_process_endorsement_event_governance(endorsement_processor_mock):

    governance = GOVERNANCE_LABEL
    event_dict = {
        "origin": governance,
        "wallet_id": governance,
        "payload": {"state": "request-received", "transaction_id": "txn1"},
    }

    event_json = json.dumps(event_dict)

    with patch(
        "endorser.services.endorsement_processor.should_accept_endorsement"
    ) as mock_should_accept_endorsement, patch(
        "endorser.services.endorsement_processor.accept_endorsement"
    ) as mock_accept_endorsement:
        mock_should_accept_endorsement.return_value = True
        mock_accept_endorsement.return_value = AsyncMock()
        await endorsement_processor_mock._process_endorsement_event(event_json)

        mock_should_accept_endorsement.assert_called_once()
        mock_accept_endorsement.assert_called_once()


@pytest.mark.anyio
async def test_handle_unprocessable_endorse_event(endorsement_processor_mock):
    key = "endorse:key"
    event_json = "event_json"
    error = Exception("Processing error")

    endorsement_processor_mock._handle_unprocessable_endorse_event(
        key, event_json, error
    )

    unprocessable_key_prefix = "unprocessable:endorse:key"
    # unprocessable key is set:
    endorsement_processor_mock.redis_service.set.assert_called_with(
        key=unprocessable_key_prefix, value=unittest.mock.ANY
    )
    # original event deleted:
    endorsement_processor_mock.redis_service.delete_key.assert_called_with(key=key)
