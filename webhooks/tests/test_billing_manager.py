import asyncio
from itertools import chain, repeat
from unittest.mock import AsyncMock, MagicMock, Mock

from fastapi import HTTPException
from httpx import Response
import pytest
from redis.cluster import ClusterPubSub
from shared.constants import LAGO_URL
from webhooks.services.billing_manager import BillingManager
from webhooks.models.billing_payloads import (
    AttribBillingEvent,
    CredDefBillingEvent,
    CredentialBillingEvent,
    LagoEvent,
    ProofBillingEvent,
    RevocationBillingEvent,
    RevRegDefBillingEvent,
    RevRegEntryBillingEvent,
)


@pytest.fixture
def redis_service_mock():
    redis_service = MagicMock()
    redis_service.get_billing_event = Mock()
    return redis_service


@pytest.fixture
def billing_manager_mock(redis_service_mock):
    billing_manager = BillingManager(redis_service=redis_service_mock)
    billing_manager._pubsub = Mock(spec=ClusterPubSub)
    billing_manager._client.post = AsyncMock(return_value=Response(200, json="Success"))
    return billing_manager


@pytest.mark.anyio
async def test_start_and_tasks_are_running(billing_manager_mock):
    billing_manager_mock._listen_for_billing_events = AsyncMock()

    billing_manager_mock.start()
    if billing_manager_mock.lago_api_key:
        assert len(billing_manager_mock._tasks) > 0
    assert billing_manager_mock.are_tasks_running()


@pytest.mark.anyio
async def test_stop(billing_manager_mock):
    mock_task = asyncio.create_task(asyncio.sleep(1))
    billing_manager_mock._tasks.append(mock_task)

    billing_manager_mock._pubsub = Mock()

    await billing_manager_mock.stop()

    assert mock_task.cancelled()
    assert len(billing_manager_mock._tasks) == 0

    billing_manager_mock._pubsub.disconnect.assert_called_once()


@pytest.mark.anyio
@pytest.mark.parametrize("message", [{"data": b"GroupA:123456789"}, {}])
async def test_listen_for_billing_events(billing_manager_mock, message):
    pubsub_mock = billing_manager_mock.redis_service.redis.pubsub.return_value
    pubsub_mock.subscribe = Mock()
    pubsub_mock.get_message = Mock(side_effect=chain([message], repeat(None)))

    try:
        await asyncio.wait_for(
            billing_manager_mock._listen_for_billing_events(), timeout=0.5
        )
    except asyncio.TimeoutError:
        pass

    billing_manager_mock.redis_service.redis.pubsub.assert_called_once()
    billing_manager_mock._pubsub.subscribe.assert_called_once_with(
        billing_manager_mock.redis_service.billing_event_pubsub_channel
    )
    billing_manager_mock._pubsub.get_message.assert_called_once_with(
        ignore_subscribe_messages=True
    )
    assert billing_manager_mock._pubsub.get_message.call_count >= 1


@pytest.mark.anyio
@pytest.mark.parametrize(
    "topic, payload_id, transaction_id, expected_lago_event",
    [
        (
            "credentials",
            "thread_id",
            "123456789",
            CredentialBillingEvent(
                transaction_id="123456789", external_customer_id="GroupA"
            ),
        ),
        (
            "proofs",
            "thread_id",
            "123456789",
            ProofBillingEvent(
                transaction_id="123456789", external_customer_id="GroupA"
            ),
        ),
        (
            "issuer_cred_rev",
            "record_id",
            "123456789",
            RevocationBillingEvent(
                transaction_id="123456789", external_customer_id="GroupA"
            ),
        ),
        ("credentials", "thread_id", "", None),
        ("proofs", "thread_id", "", None),
        ("issuer_cred_rev", "record_id", "", None),
        ("not a topic", "thread_id", "123456789", None),
    ],
)
async def test_process_billing_event(
    billing_manager_mock, topic, payload_id, transaction_id, expected_lago_event
):
    billing_manager_mock._post_billing_event = AsyncMock()
    dummy_message = {"data": b"GroupA:123456789"}
    dummy_event_data = (
        f'{{"topic": "{topic}","payload": {{"{payload_id}": "{transaction_id}"}}}}'
    )
    billing_manager_mock.redis_service.get_billing_event.return_value = [
        dummy_event_data
    ]

    await billing_manager_mock._process_billing_event(dummy_message)

    billing_manager_mock.redis_service.get_billing_event.assert_called_once_with(
        "GroupA", 123456789, 123456789
    )
    if expected_lago_event:
        billing_manager_mock._post_billing_event.assert_called_once_with(
            expected_lago_event
        )
    else:
        billing_manager_mock._post_billing_event.assert_not_called()


@pytest.mark.anyio
async def test_process_billing_event_x(billing_manager_mock):
    billing_manager_mock._post_billing_event = AsyncMock()
    dummy_message = {"data": b"GroupA:123456789"}
    billing_manager_mock.redis_service.get_billing_event.return_value = None

    await billing_manager_mock._process_billing_event(dummy_message)

    billing_manager_mock.redis_service.get_billing_event.assert_called_once_with(
        "GroupA", 123456789, 123456789
    )
    billing_manager_mock._post_billing_event.assert_not_called()


@pytest.mark.anyio
async def test_process_2_billing_events(billing_manager_mock):
    billing_manager_mock._post_billing_event = AsyncMock()
    dummy_message = {"data": b"GroupA:123456789"}
    dummy_event_data = [
        '{"topic": "credentials","payload": {"thread_id": "123456"}}',
        '{"topic": "proofs","payload": {"thread_id": "123456"}}',
    ]
    billing_manager_mock.redis_service.get_billing_event.return_value = dummy_event_data

    await billing_manager_mock._process_billing_event(dummy_message)

    billing_manager_mock.redis_service.get_billing_event.assert_called_once_with(
        "GroupA", 123456789, 123456789
    )

    billing_manager_mock._post_billing_event.assert_called_once_with(
        CredentialBillingEvent(transaction_id="123456", external_customer_id="GroupA")
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "payload_type, expected_event_type",
    [
        ("100", AttribBillingEvent),
        ("102", CredDefBillingEvent),
        ("113", RevRegDefBillingEvent),
        ("114", RevRegEntryBillingEvent),
        ("not a type", None),
    ],
)
async def test_process_endorsements_event(
    billing_manager_mock, payload_type, expected_event_type
):
    billing_manager_mock._post_billing_event = AsyncMock()
    dummy_message = {"data": b"GroupA:123456789"}

    if not expected_event_type:
        billing_manager_mock.redis_service.get_billing_event.return_value = [
            f'{{"topic": "endorsements","payload": {{"transaction_id": "123456789","type": "{payload_type}"}}}}'
        ]
        billing_manager_mock._convert_endorsements_event = Mock(return_value=None)
        await billing_manager_mock._process_billing_event(dummy_message)
        billing_manager_mock._convert_endorsements_event.assert_called_once_with(
            group_id="GroupA", endorsement_type=payload_type, transaction_id="123456789"
        )
        billing_manager_mock._post_billing_event.assert_not_called()

        return

    dummy_lago = expected_event_type(
        transaction_id="123456789", external_customer_id="GroupA"
    )
    billing_manager_mock.redis_service.get_billing_event.return_value = [
        f'{{"topic": "endorsements","payload": {{"transaction_id": "123456789","type": "{payload_type}"}}}}'
    ]
    billing_manager_mock._convert_endorsements_event = Mock(return_value=dummy_lago)

    await billing_manager_mock._process_billing_event(dummy_message)

    billing_manager_mock.redis_service.get_billing_event.assert_called_once_with(
        "GroupA", 123456789, 123456789
    )
    billing_manager_mock._convert_endorsements_event.assert_called_once_with(
        group_id="GroupA", endorsement_type=payload_type, transaction_id="123456789"
    )
    billing_manager_mock._post_billing_event.assert_called_once_with(dummy_lago)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "group_id, endorsement_type, transaction_id, expected_event_type",
    [
        ("GroupA", "100", "123456789", AttribBillingEvent),
        ("GroupA", "102", "123456789", CredDefBillingEvent),
        ("GroupA", "113", "123456789", RevRegDefBillingEvent),
        ("GroupA", "114", "123456789", RevRegEntryBillingEvent),
        ("GroupA", "notanumber", "123456789", None),
        ("GroupA", "100", None, None),
    ],
)
async def test_convert_endorsements_event(
    billing_manager_mock,
    group_id,
    endorsement_type,
    transaction_id,
    expected_event_type,
):

    lago = billing_manager_mock._convert_endorsements_event(
        group_id=group_id,
        endorsement_type=endorsement_type,
        transaction_id=transaction_id,
    )

    if not expected_event_type or not transaction_id:
        assert lago is None
        return

    expected_lago = expected_event_type(
        transaction_id="123456789", external_customer_id="GroupA"
    )

    assert lago == expected_lago


@pytest.mark.anyio
async def test_post_billing_event(billing_manager_mock):
    event = LagoEvent(transaction_id="123", external_customer_id="456")

    await billing_manager_mock._post_billing_event(event)

    billing_manager_mock._client.post.assert_called_once_with(
        url=LAGO_URL, json={"event": event.model_dump()}
    )

@pytest.mark.anyio
@pytest.mark.parametrize("status_code, detail", [(422, "value_already_exist"), (500, "server_error")])
async def test_post_billing_event_x(billing_manager_mock,status_code,detail):
    event = LagoEvent(transaction_id="123", external_customer_id="456")

    billing_manager_mock._client.post = AsyncMock(side_effect=HTTPException(status_code,detail=detail))

    await billing_manager_mock._post_billing_event(event)

    billing_manager_mock._client.post.assert_called_once_with(
        url=LAGO_URL, json={"event": event.model_dump()}
    )
