import pytest
from httpx import AsyncClient

from app.constants import WEBHOOKS_URL
from app.tests.util.ecosystem_connections import BobAliceConnect
from app.tests.util.webhooks import get_wallet_id_from_async_client
from shared import RichAsyncClient
from webhooks.main import app


@pytest.mark.anyio
async def test_connection_webhooks(
    alice_member_client: RichAsyncClient, bob_and_alice_connection: BobAliceConnect
):
    async with AsyncClient(app=app, base_url=WEBHOOKS_URL) as client:
        alice_wallet_id = get_wallet_id_from_async_client(alice_member_client)
        alice_connection_id = bob_and_alice_connection.alice_connection_id

        response = await client.get(f"/webhooks/{alice_wallet_id}")
        assert response.status_code == 200

        response_text = response.text
        assert '"topic":"connections"' in response_text
        assert f'"connection_id":"{alice_connection_id}"' in response_text
        assert f'"wallet_id":"{alice_wallet_id}"' in response_text
