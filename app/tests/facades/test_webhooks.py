from unittest.mock import patch

import pytest

import app.facades.webhooks as whf
from shared import Connection

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
async def test_get_hooks_per_topic_per_wallet():
    with patch.object(
        whf, "get_hooks_per_topic_per_wallet"
    ) as mock_hook_by_topic_wallet:
        mock_hook_by_topic_wallet.return_value = [conn_record]
        whf.get_hooks_per_topic_per_wallet(wallet_id="wallet_id", topic="connections")

        mock_hook_by_topic_wallet.assert_called_once_with(
            wallet_id="wallet_id", topic="connections"
        )


@pytest.mark.anyio
async def test_get_hooks_per_wallet():
    with patch.object(whf, "get_hooks_per_wallet") as mock_get_hooks_per_wallet:
        whf.get_hooks_per_wallet.return_value = [conn_record]
        whf.get_hooks_per_wallet(wallet_id="wallet_id")

        mock_get_hooks_per_wallet.assert_called_once_with(wallet_id="wallet_id")
