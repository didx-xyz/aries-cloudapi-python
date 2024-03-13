from unittest.mock import AsyncMock, patch

import pytest
from fastapi import WebSocket

from app.event_handling.websocket_manager import (
    WebsocketManager,
    convert_url_to_websocket,
)


@pytest.fixture(autouse=True)
def mock_pubsub_client():
    with patch(
        "app.event_handling.websocket_manager.PubSubClient", autospec=True
    ) as mock_client:
        mock_client.return_value.wait_until_ready = AsyncMock()
        mock_client.return_value.disconnect = AsyncMock()
        yield mock_client


@pytest.mark.anyio
async def test_subscribe_wallet_id_and_topic(mock_pubsub_client):
    websocket = AsyncMock(spec=WebSocket)
    wallet_id = "test_wallet_id"
    topic = "test_topic"

    await WebsocketManager.subscribe(websocket, wallet_id=wallet_id, topic=topic)

    # Ensure `subscribe` was called once
    mock_pubsub_client.assert_called_once()
    mock_pubsub_client.return_value.subscribe.assert_called_once()

    # Check that the callback is working as expected
    callback_func = mock_pubsub_client.return_value.subscribe.call_args[0][1]
    dummy_data = "dummy_data"
    await callback_func(dummy_data, "dummy_topic")

    # Check that the websocket's `send_text` method was called with the correct argument
    websocket.send_text.assert_called_once_with(dummy_data)


def test_convert_url_to_websocket():
    assert convert_url_to_websocket("http://example.com") == "ws://example.com"
    assert convert_url_to_websocket("https://example.com") == "wss://example.com"
