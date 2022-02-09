import pytest
from unittest.mock import patch

from aries_cloudcontroller import AcaPyClient

import app.facades.webhooks as whf
from app.generic.models import ConnectionsHook

client = AcaPyClient(
    base_url="xyz",
    api_key="abcd",
    tenant_jwt="member.eyJ3YWxsZXRfaWQiOiIwMzg4OTc0MC1iNDg4LTRmZjEtYWI4Ni0yOTM0NzQwZjNjNWMifQ",
)

conn_record = ConnectionsHook(
    accept="auto",
    connection_id="abcd",
    connection_protocol="connections/1.0",
    created_at="abcd",
    invitation_mode="once",
    rfc23_state="start",
    state="request",
    their_role="inviter",
    updated_at="now",
)


@pytest.mark.asyncio
async def test_get_wallet_id_from_client(client: AcaPyClient = client):

    result = whf.get_wallet_id_from_client(client)

    assert result == "03889740-b488-4ff1-ab86-2934740f3c5c"


@pytest.mark.asyncio
async def test_get_hooks_per_topic_per_wallet():

    with patch.object(
        whf, "get_hooks_per_topic_per_wallet"
    ) as mock_hook_by_topic_wallet:
        mock_hook_by_topic_wallet.return_value = [conn_record]
        whf.get_hooks_per_topic_per_wallet(client=client, topic="connections")

        mock_hook_by_topic_wallet.assert_called_once_with(
            client=client, topic="connections"
        )


@pytest.mark.asyncio
async def test_get_hooks_per_topic_admin():
    with patch.object(
        whf, "get_hooks_per_topic_admin"
    ) as mock_get_hooks_per_topic_admin:
        whf.get_hooks_per_topic_admin.return_value = [conn_record]
        whf.get_hooks_per_topic_admin(client=client, topic="connections")

        mock_get_hooks_per_topic_admin.assert_called_once_with(
            client=client, topic="connections"
        )
