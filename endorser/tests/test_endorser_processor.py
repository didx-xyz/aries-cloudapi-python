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
    # Mock the EndorsementProcessor methods
    processor._start_notification_listener = Mock()
    # Mock pubsub
    processor._pubsub_thread = Mock(spec=PubSubWorkerThread)
    processor._pubsub_thread.is_alive.return_value = True
    processor._pubsub = Mock(spec=ClusterPubSub)
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
    endorsement_processor_mock._tasks = [asyncio.create_task(asyncio.sleep(1))]
    await endorsement_processor_mock.stop()
    # Task has been cancelled, it should be considered not running
    assert not endorsement_processor_mock.are_tasks_running()

    # Now test that is starts as normal:
    endorsement_processor_mock._process_endorsement_requests = AsyncMock()
    endorsement_processor_mock.start()
    assert endorsement_processor_mock.are_tasks_running()

    # when pubsub thread stops, tasks should be not running
    endorsement_processor_mock._pubsub_thread.is_alive.return_value = False
    assert not endorsement_processor_mock.are_tasks_running()


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
