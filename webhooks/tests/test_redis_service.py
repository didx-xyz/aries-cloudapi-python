from unittest.mock import AsyncMock

import pytest

from shared.models.webhook_topics.base import CloudApiWebhookEventGeneric
from webhooks.dependencies.redis_service import RedisService

wallet_id = "test_wallet"
topic = "test_topic"
payload = '"payload": {"test":"1"}'

json_entries = [
    f'{{"wallet_id": "{wallet_id}", "topic": "{topic}", "origin": "a", {payload}}}',
    f'{{"wallet_id": "{wallet_id}", "topic": "{topic}", "origin": "a", {payload}}}',
]
cloudapi_entries = [
    CloudApiWebhookEventGeneric(
        wallet_id=wallet_id, topic=topic, origin="a", payload={"test": "1"}
    ),
    CloudApiWebhookEventGeneric(
        wallet_id=wallet_id, topic=topic, origin="a", payload={"test": "1"}
    ),
]


@pytest.mark.anyio
async def test_add_webhook_event():
    event_json = json_entries[0]

    # Create a mock Redis client with the methods you want to test
    redis_client = AsyncMock()
    redis_client.zadd = AsyncMock()
    redis_client.publish = AsyncMock()

    # Initialize RedisService with the mocked Redis client
    redis_service = RedisService(redis_client)

    # Call the method you want to test
    await redis_service.add_webhook_event(event_json, wallet_id)

    # Assert that the mocked methods were called as expected
    redis_client.zadd.assert_called_once()
    redis_client.publish.assert_called_once()


@pytest.mark.anyio
async def test_get_json_webhook_events_by_wallet():
    redis_client = AsyncMock()
    redis_client.zrange = AsyncMock(return_value=[e.encode() for e in json_entries])
    redis_service = RedisService(redis_client)

    events = await redis_service.get_json_webhook_events_by_wallet(wallet_id)

    assert events == json_entries
    redis_client.zrange.assert_called_once()


@pytest.mark.anyio
async def test_get_webhook_events_by_wallet(mocker):
    expected_events = cloudapi_entries

    redis_service = RedisService(AsyncMock())
    mocker.patch.object(
        redis_service, "get_json_webhook_events_by_wallet", return_value=json_entries
    )
    mocker.patch(
        "shared.util.rich_parsing.parse_with_error_handling",
        side_effect=expected_events,
    )

    events = await redis_service.get_webhook_events_by_wallet(wallet_id)

    assert events == expected_events


@pytest.mark.anyio
async def test_get_json_webhook_events_by_wallet_and_topic(mocker):
    different_json = [
        '{"payload":{"test":"1"},"topic":"test_topic"}',
        '{"payload":{"test":"2"},"topic":"other_topic"}',
    ]
    expected_events = ['{"payload":{"test":"1"},"topic":"test_topic"}']

    redis_service = RedisService(AsyncMock())
    mocker.patch.object(
        redis_service, "get_json_webhook_events_by_wallet", return_value=different_json
    )

    events = await redis_service.get_json_webhook_events_by_wallet_and_topic(
        wallet_id="test_wallet_id", topic=topic
    )

    assert events == expected_events


@pytest.mark.anyio
async def test_get_webhook_events_by_wallet_and_topic(mocker):
    event_instances = [
        CloudApiWebhookEventGeneric(
            wallet_id=wallet_id, topic=topic, origin="a", payload={"test": "1"}
        ),
        CloudApiWebhookEventGeneric(
            wallet_id=wallet_id, topic="other", origin="a", payload={"test": "2"}
        ),
    ]
    expected_events = [event_instances[0]]

    redis_service = RedisService(AsyncMock())
    mocker.patch.object(
        redis_service, "get_webhook_events_by_wallet", return_value=event_instances
    )

    events = await redis_service.get_webhook_events_by_wallet_and_topic(
        wallet_id, topic
    )

    assert events == expected_events


@pytest.mark.anyio
async def test_get_json_events_by_timestamp():
    start_timestamp = 1609459200
    end_timestamp = 1609545600

    redis_client = AsyncMock()
    redis_client.zrangebyscore = AsyncMock(
        return_value=[e.encode() for e in json_entries]
    )

    redis_service = RedisService(redis_client)

    events = await redis_service.get_json_events_by_timestamp(
        wallet_id, start_timestamp, end_timestamp
    )

    assert events == json_entries
    redis_client.zrangebyscore.assert_called_once_with(
        f"wallet_id:{wallet_id}", min=start_timestamp, max=end_timestamp
    )


@pytest.mark.anyio
async def test_get_events_by_timestamp(mocker):
    start_timestamp = 1609459200
    end_timestamp = 1609545600

    redis_service = RedisService(AsyncMock())
    mocker.patch.object(
        redis_service, "get_json_events_by_timestamp", return_value=json_entries
    )
    mocker.patch(
        "shared.util.rich_parsing.parse_with_error_handling",
        side_effect=cloudapi_entries,
    )

    events = await redis_service.get_events_by_timestamp(
        wallet_id, start_timestamp, end_timestamp
    )

    assert events == cloudapi_entries


@pytest.mark.anyio
async def test_get_all_wallet_ids():
    expected_wallet_ids = ["wallet1", "wallet2", "wallet3"]
    scan_results = [
        (
            1,
            [
                f"wallet_id:{wallet_id}".encode()
                for wallet_id in expected_wallet_ids[:2]
            ],
        ),
        (0, [f"wallet_id:{expected_wallet_ids[2]}".encode()]),
    ]

    redis_client = AsyncMock()
    redis_client.scan = AsyncMock(side_effect=scan_results)

    redis_service = RedisService(redis_client)

    wallet_ids = await redis_service.get_all_wallet_ids()

    assert set(wallet_ids) == set(expected_wallet_ids)
    assert redis_client.scan.call_count == 2
