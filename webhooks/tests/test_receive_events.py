from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from shared.models.webhook_topics.base import CloudApiWebhookEvent
from webhooks.web.main import app

client = TestClient(app)

origin = "test_origin"
dummy_event = CloudApiWebhookEvent(
    wallet_id="test_wallet", topic="test_topic", origin=origin, payload={}
)


@patch(
    "webhooks.models.acapy_to_cloudapi_event",
    return_value=dummy_event,
)
@patch(
    "webhooks.services.redis_service.WebhooksRedisService.add_cloudapi_webhook_event",
    new_callable=AsyncMock,
)
def test_topic_root(mock_add_webhook_event, _):
    # Prepare the request payload
    acapy_topic = "connections"
    body = {"payload": "test"}
    headers = {"x-wallet-id": "test_wallet"}

    # Make the POST request
    response = client.post(f"/{origin}/topic/{acapy_topic}", json=body, headers=headers)

    # Verify the response
    assert response.status_code == 204

    # Verify that the Redis service was called
    mock_add_webhook_event.assert_awaited_once()
