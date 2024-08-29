import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from redis.client import PubSubWorkerThread
from redis.cluster import ClusterPubSub

from shared.constants import GOVERNANCE_LABEL, SET_LOCKS
from webhooks.services.acapy_events_processor import AcaPyEventsProcessor

# pylint: disable=redefined-outer-name
# because re-using fixtures in same module
# pylint: disable=protected-access
# because we are testing protected methods


@pytest.fixture
def redis_service_mock():
    redis_service = MagicMock()
    redis_service.acapy_redis_prefix = "acapy-record-*"
    redis_service.add_cloudapi_webhook_event = Mock()
    redis_service.add_endorsement_event = Mock()
    return redis_service


@pytest.fixture
def acapy_events_processor_mock(redis_service_mock):
    processor = AcaPyEventsProcessor(redis_service=redis_service_mock)
    # Mock pubsub
    processor._pubsub_thread = Mock(spec=PubSubWorkerThread)
    processor._pubsub_thread.is_alive.return_value = True
    processor._pubsub = Mock(spec=ClusterPubSub)

    return processor


@pytest.mark.anyio
async def test_start_and_tasks_are_running(acapy_events_processor_mock):
    acapy_events_processor_mock._process_incoming_events = AsyncMock()

    acapy_events_processor_mock.start()
    # Ensure background tasks are started
    assert len(acapy_events_processor_mock._tasks) > 0
    assert acapy_events_processor_mock.are_tasks_running()


@pytest.mark.anyio
async def test_stop(acapy_events_processor_mock):
    # Setup a dummy task to simulate an ongoing task
    dummy_task = asyncio.create_task(asyncio.sleep(1))
    acapy_events_processor_mock._tasks.append(dummy_task)

    # Simulate an existing pubsub_thread and pubsub instance
    # acapy_events_processor_mock._pubsub_thread = Mock(spec=PubSubWorkerThread)
    acapy_events_processor_mock._pubsub = Mock()

    await acapy_events_processor_mock.stop()

    # Check that all tasks were attempted to be cancelled
    assert dummy_task.cancelled()

    # Ensure tasks list is cleared
    assert len(acapy_events_processor_mock._tasks) == 0

    # Verify that pubsub_thread stop and pubsub disconnect methods were called
    acapy_events_processor_mock._pubsub_thread.stop.assert_called_once()
    acapy_events_processor_mock._pubsub.disconnect.assert_called_once()


@pytest.mark.anyio
async def test_are_tasks_running_x(acapy_events_processor_mock):
    acapy_events_processor_mock._tasks = []
    # Since we didn't start a task, it should be considered not running
    assert not acapy_events_processor_mock.are_tasks_running()

    # Create dummy task and stop it
    dummy_done_task = MagicMock()
    dummy_done_task.done.return_value = True
    acapy_events_processor_mock._tasks = [dummy_done_task]

    # Task has been cancelled, it should be considered not running
    assert not acapy_events_processor_mock.are_tasks_running()

    # Now reset task to appear as still running, to test pubsub thread case
    dummy_done_task.done.return_value = False
    acapy_events_processor_mock._tasks = [dummy_done_task]
    # when pubsub thread stops, tasks should be not running

    # todo: uncomment these tests after reimplemented:
    # acapy_events_processor_mock._pubsub_thread.is_alive.return_value = False
    # assert not acapy_events_processor_mock.are_tasks_running()


@pytest.mark.anyio
async def test_rpush_notification_handler(acapy_events_processor_mock):
    acapy_events_processor_mock._new_event_notification = Mock()

    # Call the method with the mocked message
    acapy_events_processor_mock._rpush_notification_handler(Mock())

    # Verify that _new_event_notification.set() was called
    acapy_events_processor_mock._new_event_notification.set.assert_called_once_with()


def test_start_notification_listener(acapy_events_processor_mock):
    acapy_events_processor_mock._pubsub.psubscribe = Mock()
    acapy_events_processor_mock._pubsub.run_in_thread = Mock()

    # Call the method
    acapy_events_processor_mock._start_notification_listener()

    # Verify psubscribe and run_in_thread was called correctly
    acapy_events_processor_mock._pubsub.psubscribe.assert_called_once()
    acapy_events_processor_mock._pubsub.run_in_thread.assert_called_once()


@pytest.mark.anyio
async def test_process_incoming_events(acapy_events_processor_mock):
    scan_results = [
        [],  # empty list to start
        ["acapy-record-wallet1"],  # Then a key returned from the scan
        ["acapy-record-wallet2", "acapy-record-wallet3"],  # Then 2 keys in a batch
        Exception(
            "Force inf loop to stop"
        ),  # force loop to exit after processing available keys
    ]
    redis_service = Mock()
    redis_service.scan_keys = Mock(side_effect=scan_results)
    acapy_events_processor_mock.redis_service = redis_service

    # Store processed keys for assertion
    processed_keys = []

    # Override _attempt_process_list_events to track keys and then set the done_event
    def mock_attempt_process_list_events(key):
        processed_keys.append(key)

    acapy_events_processor_mock._attempt_process_list_events = (
        mock_attempt_process_list_events
    )

    # Exception is to force the NoReturn function to exit
    with pytest.raises(Exception):
        await acapy_events_processor_mock._process_incoming_events()

    # Assert that the keys were processed
    assert len(processed_keys) == 3
    assert processed_keys == [
        "acapy-record-wallet1",
        "acapy-record-wallet2",
        "acapy-record-wallet3",
    ]


@pytest.mark.anyio
async def test_attempt_process_list_events(acapy_events_processor_mock):
    event_key = "acapy-record-wallet1"
    lock_key = f"lock:{event_key}"
    acapy_events_processor_mock.redis_service.set_lock.return_value = True
    acapy_events_processor_mock._process_list_events = Mock()

    acapy_events_processor_mock._attempt_process_list_events(event_key)

    acapy_events_processor_mock._process_list_events.assert_called_with(event_key)
    if SET_LOCKS:
        acapy_events_processor_mock.redis_service.set_lock.assert_called_with(
            lock_key, px=3000
        )
        acapy_events_processor_mock.redis_service.delete_key.assert_called_with(
            lock_key
        )


@pytest.mark.anyio
async def test_attempt_process_list_events_x(acapy_events_processor_mock):
    acapy_events_processor_mock._handle_unprocessable_event = Mock()
    acapy_events_processor_mock._process_list_events = Mock(
        side_effect=Exception("Test")
    )
    acapy_events_processor_mock._attempt_process_list_events("key")

    # Assert _handle_unprocessable_event is called when exception was raised
    acapy_events_processor_mock._handle_unprocessable_event.assert_called_once()


@pytest.mark.anyio
async def test_process_list_events_with_data(acapy_events_processor_mock):
    # Mock `lindex` to return a JSON string, and then None (signalling end of list)
    acapy_events_processor_mock.redis_service.lindex = Mock(
        side_effect=[b'{"some":"data"}', None]
    )
    # and `pop_first_list_element` to return True
    acapy_events_processor_mock.redis_service.pop_first_list_element.return_value = True

    # Mock `_process_event` to simply pass
    acapy_events_processor_mock._process_event = Mock()

    list_key = "acapy-record-wallet1"
    acapy_events_processor_mock._process_list_events(list_key)

    # Verify lindex and pop_first_list_element were called with the list_key
    acapy_events_processor_mock.redis_service.lindex.assert_called_with(list_key)
    acapy_events_processor_mock.redis_service.pop_first_list_element.assert_called_with(
        list_key
    )
    # Verify _process_event was called with the mocked event_json
    acapy_events_processor_mock._process_event.assert_called_once_with(
        '{"some":"data"}'
    )
    assert acapy_events_processor_mock.redis_service.lindex.call_count == 2


@pytest.mark.anyio
async def test_process_list_events_empty_list(acapy_events_processor_mock):
    # Mock `lindex` to return None, simulating an empty list
    acapy_events_processor_mock.redis_service.lindex.return_value = None

    list_key = "acapy-record-empty"
    acapy_events_processor_mock._process_list_events(list_key)

    # Verify lindex was called with the list_key, and verify pop_first_list_element was never called
    acapy_events_processor_mock.redis_service.lindex.assert_called_once_with(list_key)
    acapy_events_processor_mock.redis_service.pop_first_list_element.assert_not_called()


@pytest.mark.anyio
async def test_process_list_events_raises_exception(acapy_events_processor_mock):
    # Mock `lindex` to raise an exception
    acapy_events_processor_mock.redis_service.lindex.side_effect = Exception(
        "Test error"
    )

    list_key = "acapy-record-error"
    with pytest.raises(Exception, match="Test error"):
        acapy_events_processor_mock._process_list_events(list_key)


@pytest.mark.anyio
async def test_process_event_valid_data(acapy_events_processor_mock):
    event_dict = {
        "payload": {
            "wallet_id": "base",
            "state": "invitation",
            "topic": "acapy::record::connections::invitation",
            "category": "connections",
            "payload": {
                "state": "invitation",
                "created_at": "2024-03-07T09:34:00.405139Z",
                "updated_at": "2024-03-07T09:34:00.405139Z",
                "connection_id": "f5fda7d3-8beb-4d83-8ded-136397229767",
                "their_role": "invitee",
                "connection_protocol": "didexchange/1.0",
                "rfc23_state": "invitation-sent",
                "invitation_key": "7LRhtTiK8HNcP7Q823T2xrb29afvxjR6WYHghrrgGxHo",
                "invitation_msg_id": "21065ab5-febd-45dc-aaac-97a0e787b8f4",
                "accept": "auto",
                "invitation_mode": "once",
                "alias": "faber_XFUQS",
            },
        },
        "metadata": {"time_ns": 1709804040410284107, "origin": "Governance"},
    }
    event_json = json.dumps(event_dict)

    acapy_events_processor_mock._process_event(event_json)

    # Assert that add_cloudapi_webhook_event was called with the mock event
    acapy_events_processor_mock.redis_service.add_cloudapi_webhook_event.assert_called()
    acapy_events_processor_mock.redis_service.add_endorsement_event.assert_not_called()


@pytest.mark.anyio
async def test_process_event_with_applicable_endorsement(
    acapy_events_processor_mock, mocker
):
    event_dict = {
        "payload": {
            "wallet_id": GOVERNANCE_LABEL,
            "topic": "acapy::record::endorse_transaction",
            "category": "endorse_transaction",
            "payload": {"state": "request-received", "transaction_id": "txn1"},
        },
        "metadata": {"time_ns": 1709804040410284107, "origin": GOVERNANCE_LABEL},
    }
    event_json = json.dumps(event_dict)

    # Ensure `payload_is_applicable_for_endorser` returns True
    mocker.patch(
        "webhooks.services.acapy_events_processor.payload_is_applicable_for_endorser",
        return_value=True,
    )

    acapy_events_processor_mock._process_event(event_json)

    # Verify that add_endorsement_event was called with the mock event JSON
    acapy_events_processor_mock.redis_service.add_endorsement_event.assert_called_once()


@pytest.mark.anyio
async def test_handle_unprocessable_event(acapy_events_processor_mock):
    key = "acapy-record-key"
    event_json = "event_json"
    error = Exception("Processing error")

    acapy_events_processor_mock.redis_service.pop_first_list_element.return_value = (
        event_json
    )

    acapy_events_processor_mock._handle_unprocessable_event(key, error)

    expected_error_message = f"Could not process: {event_json}. Error: {error}"

    # unprocessable key is set (key contains uuid)
    acapy_events_processor_mock.redis_service.set.assert_called_with(
        key=unittest.mock.ANY, value=expected_error_message
    )


@pytest.mark.anyio
async def test_obfuscate_sensitive_data_endorse_transaction(
    acapy_events_processor_mock, mocker
):
    acapy_topic = "endorse_transaction"
    payload = {"some_key": "some_value"}
    obfuscated_payload = {"obfuscated": "payload"}
    mocker.patch(
        "webhooks.services.acapy_events_processor.obfuscate_primary_data_in_payload",
        return_value=obfuscated_payload,
    )

    result = acapy_events_processor_mock._obfuscate_sensitive_data(acapy_topic, payload)

    assert result == obfuscated_payload


@pytest.mark.anyio
async def test_obfuscate_sensitive_data_issue_credential_v2_0_indy(
    acapy_events_processor_mock,
):
    acapy_topic = "issue_credential_v2_0_indy"
    payload = {
        "cred_request_metadata": {
            "master_secret_blinding_data": {
                "v_prime": "sensitive_data_v_prime",
                "vr_prime": "sensitive_data_vr_prime",
                "other_field": "unchanged_data",
            }
        }
    }

    expected_payload = payload.copy()
    expected_payload["cred_request_metadata"]["master_secret_blinding_data"][
        "v_prime"
    ] = "REDACTED"
    expected_payload["cred_request_metadata"]["master_secret_blinding_data"][
        "vr_prime"
    ] = "REDACTED"

    result = acapy_events_processor_mock._obfuscate_sensitive_data(acapy_topic, payload)

    assert result == expected_payload


@pytest.mark.anyio
async def test_obfuscate_sensitive_data_other(acapy_events_processor_mock):
    # Other topics should be unchanged
    acapy_topic = "other"
    payload = {"some_key": "some_value"}

    result = acapy_events_processor_mock._obfuscate_sensitive_data(acapy_topic, payload)

    assert result == payload
