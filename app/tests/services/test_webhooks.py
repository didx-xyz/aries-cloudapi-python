from unittest.mock import AsyncMock, patch

import pytest

import app.services.webhooks as whf
from shared.models.webhook_topics import Connection

conn_record = Connection(
    accept="auto",
    connection_id="abcd",
    connection_protocol="connections/1.0",
    created_at="abcd",
    invitation_mode="once",
    state="active",
    their_role="inviter",
    updated_at="now",
)


@pytest.mark.anyio
async def test_get_hooks_for_wallet_by_topic():
    with patch.object(
        whf, "get_hooks_for_wallet_by_topic", new_callable=AsyncMock
    ) as mock_hook_by_wallet_and_topic:
        mock_hook_by_wallet_and_topic.return_value = [conn_record]
        await whf.get_hooks_for_wallet_by_topic(
            wallet_id="wallet_id", topic="connections"
        )

        mock_hook_by_wallet_and_topic.assert_called_once_with(
            wallet_id="wallet_id", topic="connections"
        )


@pytest.mark.anyio
async def test_get_hooks_for_wallet():
    with patch.object(
        whf, "get_hooks_for_wallet", new_callable=AsyncMock
    ) as mock_get_hooks_for_wallet:
        whf.get_hooks_for_wallet.return_value = [conn_record]
        await whf.get_hooks_for_wallet(wallet_id="wallet_id")

        mock_get_hooks_for_wallet.assert_called_once_with(wallet_id="wallet_id")
