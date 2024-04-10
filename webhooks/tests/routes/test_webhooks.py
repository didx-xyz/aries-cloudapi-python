from unittest.mock import Mock

import pytest

from shared.models.webhook_events import CloudApiWebhookEventGeneric
from webhooks.web.routers.webhooks import (
    get_webhooks_by_wallet,
    get_webhooks_by_wallet_and_topic,
)

wallet_id = "wallet123"
topic = "test_topic"
cloud_api_event = CloudApiWebhookEventGeneric(
    wallet_id=wallet_id,
    topic=topic,
    origin="test_origin",
    group_id="test_group",
    payload={"key": "value"},
)


@pytest.mark.anyio
async def test_get_webhooks_by_wallet():
    redis_service_mock = Mock()

    redis_service_mock.get_cloudapi_events_by_wallet.return_value = [cloud_api_event]

    result = await get_webhooks_by_wallet(
        wallet_id=wallet_id, redis_service=redis_service_mock
    )

    assert len(result) == 1
    assert result[0].wallet_id == wallet_id
    redis_service_mock.get_cloudapi_events_by_wallet.assert_called_once_with(
        wallet_id, num=100
    )


@pytest.mark.anyio
async def test_get_webhooks_by_wallet_empty():
    redis_service_mock = Mock()

    redis_service_mock.get_cloudapi_events_by_wallet.return_value = []

    result = await get_webhooks_by_wallet(
        wallet_id=wallet_id, redis_service=redis_service_mock
    )

    assert result == []
    redis_service_mock.get_cloudapi_events_by_wallet.assert_called_once_with(
        wallet_id, num=100
    )


@pytest.mark.anyio
async def test_get_webhooks_by_wallet_and_topic():
    redis_service_mock = Mock()

    redis_service_mock.get_cloudapi_events_by_wallet_and_topic.return_value = [
        cloud_api_event
    ]

    result = await get_webhooks_by_wallet_and_topic(
        wallet_id=wallet_id, topic=topic, redis_service=redis_service_mock
    )

    assert len(result) == 1
    assert result[0].wallet_id == wallet_id
    redis_service_mock.get_cloudapi_events_by_wallet_and_topic.assert_called_once_with(
        wallet_id=wallet_id, topic=topic, num=100
    )


@pytest.mark.anyio
async def test_get_webhooks_by_wallet_and_topic_empty():
    redis_service_mock = Mock()

    redis_service_mock.get_cloudapi_events_by_wallet_and_topic.return_value = []

    result = await get_webhooks_by_wallet_and_topic(
        wallet_id=wallet_id, topic=topic, redis_service=redis_service_mock
    )

    assert result == []
    redis_service_mock.get_cloudapi_events_by_wallet_and_topic.assert_called_once_with(
        wallet_id=wallet_id, topic=topic, num=100
    )
