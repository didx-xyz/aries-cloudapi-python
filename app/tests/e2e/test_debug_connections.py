import asyncio

import pytest

from app.tests.fixtures.member_async_clients import get_tenant_admin_client
from app.tests.util.client import get_tenant_client
from app.tests.util.connections import (
    CONNECTIONS_BASE_PATH,
    DID_BASE_PATH,
    BobAliceConnect,
    assert_both_connections_ready,
)
from app.tests.util.tenants import create_tenant
from app.tests.util.webhooks import check_webhook_state
from shared import RichAsyncClient


async def create_did_exchange(
    alice_client: RichAsyncClient,
    bob_client: RichAsyncClient,
    bob_public_did: str,
    alias: str,
):
    # Alice create invitation
    alice_connection = (
        await alice_client.post(
            f"{CONNECTIONS_BASE_PATH}/did-exchange/create-request",
            params={
                "their_public_did": bob_public_did,
                "alias": alias,
            },
        )
    ).json()

    their_did = alice_connection["my_did"]

    bob_connection = await check_webhook_state(
        client=bob_client,
        topic="connections",
        state="request-received",
        filter_map={"their_did": their_did},
    )

    bob_connection_id = bob_connection["connection_id"]
    alice_connection_id = alice_connection["connection_id"]

    # validate both connections should be active
    await assert_both_connections_ready(
        alice_client, bob_client, alice_connection_id, bob_connection_id
    )

    return BobAliceConnect(
        alice_connection_id=alice_connection_id, bob_connection_id=bob_connection_id
    )


@pytest.mark.anyio
async def test_multiple_connections(faber_client: RichAsyncClient):
    # Initialize admin client
    await asyncio.sleep(15)
    async with get_tenant_admin_client() as admin_client:
        # Fetch issuer's public DID once
        did_response = (await faber_client.get(f"{DID_BASE_PATH}/public")).json()
        issuer_public_did = did_response["did"]

        # Number of connections to simulate
        num_connections = 10

        # List to hold tasks
        tasks = []

        for i in range(num_connections):
            alice_name = f"alice-{i}"
            # Create a new tenant for each connection
            alice_tenant = await create_tenant(admin_client, alice_name)

            # Initialize clients for Alice and Bob
            alice_client = get_tenant_client(
                token=alice_tenant.access_token, name=alice_name
            )

            # Alias for connections
            alias = f"test-connection-{i}"

            # Create connection task
            task = create_did_exchange(
                alice_client, faber_client, issuer_public_did, alias
            )

            tasks.append(task)

        # Run all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                pytest.exit(f"Connection {i} failed with exception: {result}")
            else:
                print(f"Connection {i} succeeded: {result}")
