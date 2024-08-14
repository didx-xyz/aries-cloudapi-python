import pytest

from app.routes.connections import router as connections_router
from app.tests.util.connections import create_bob_alice_connection
from app.tests.util.webhooks import get_wallet_id_from_async_client
from shared import WEBHOOKS_URL, RichAsyncClient

CONNECTIONS_BASE_PATH = connections_router.prefix


@pytest.mark.anyio
async def test_wallets_webhooks(
    alice_member_client: RichAsyncClient, bob_member_client: RichAsyncClient
):
    bob_and_alice_connection = await create_bob_alice_connection(
        alice_member_client, bob_member_client, alias="temp test connection"
    )

    try:
        async with RichAsyncClient(base_url=WEBHOOKS_URL) as client:
            alice_wallet_id = get_wallet_id_from_async_client(alice_member_client)
            alice_connection_id = bob_and_alice_connection.alice_connection_id

            response = await client.get(f"/webhooks/{alice_wallet_id}")
            assert response.status_code == 200

            response_text = response.text
            assert '"topic":"connections"' in response_text
            assert f'"connection_id":"{alice_connection_id}"' in response_text
            assert f'"wallet_id":"{alice_wallet_id}"' in response_text

    finally:
        # Clean up temp connection records
        await alice_member_client.delete(
            f"{CONNECTIONS_BASE_PATH}/{bob_and_alice_connection.alice_connection_id}"
        )
        await bob_member_client.delete(
            f"{CONNECTIONS_BASE_PATH}/{bob_and_alice_connection.bob_connection_id}"
        )


@pytest.mark.anyio
async def test_connection_webhooks(
    alice_member_client: RichAsyncClient, bob_member_client: RichAsyncClient
):
    bob_and_alice_connection = await create_bob_alice_connection(
        alice_member_client, bob_member_client, alias="temp test connection"
    )

    try:
        async with RichAsyncClient(base_url=WEBHOOKS_URL) as client:
            alice_wallet_id = get_wallet_id_from_async_client(alice_member_client)
            alice_connection_id = bob_and_alice_connection.alice_connection_id

            response = await client.get(f"/webhooks/{alice_wallet_id}/connections")
            assert response.status_code == 200

            response_text = response.text
            assert '"topic":"connections"' in response_text
            assert f'"connection_id":"{alice_connection_id}"' in response_text
            assert f'"wallet_id":"{alice_wallet_id}"' in response_text

    finally:
        # Clean up temp connection records
        await alice_member_client.delete(
            f"{CONNECTIONS_BASE_PATH}/{bob_and_alice_connection.alice_connection_id}"
        )
        await bob_member_client.delete(
            f"{CONNECTIONS_BASE_PATH}/{bob_and_alice_connection.bob_connection_id}"
        )
