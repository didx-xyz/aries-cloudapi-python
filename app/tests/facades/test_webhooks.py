from unittest.mock import patch

import pytest

import app.facades.webhooks as whf
from shared.models import Connection

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
        whf, "get_hooks_for_wallet_by_topic"
    ) as mock_hook_by_wallet_and_topic:
        mock_hook_by_wallet_and_topic.return_value = [conn_record]
        whf.get_hooks_for_wallet_by_topic(wallet_id="wallet_id", topic="connections")

        mock_hook_by_wallet_and_topic.assert_called_once_with(
            wallet_id="wallet_id", topic="connections"
        )


@pytest.mark.anyio
async def test_get_hooks_for_wallet():
    with patch.object(whf, "get_hooks_for_wallet") as mock_get_hooks_for_wallet:
        whf.get_hooks_for_wallet.return_value = [conn_record]
        whf.get_hooks_for_wallet(wallet_id="wallet_id")

        mock_get_hooks_for_wallet.assert_called_once_with(wallet_id="wallet_id")
