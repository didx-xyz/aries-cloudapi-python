from typing import TypedDict

import pytest
from httpx import AsyncClient

from app.tests.util.client import (
    ecosystem_admin_client,
    ecosystem_client,
    ecosystem_acapy_client,
)

from .tenants import create_issuer_tenant, delete_tenant
from app.tests.util.webhooks import check_webhook_state


class FaberAliceConnect(TypedDict):
    faber_connection_id: str
    alice_connection_id: str


@pytest.fixture(scope="module")
async def faber_client():
    async with ecosystem_admin_client() as client:
        tenant = await create_issuer_tenant(client, "faber")

        if "access_token" not in tenant:
            raise Exception("Error creating tenant", tenant)

        yield ecosystem_client(token=tenant["access_token"])

        await delete_tenant(client, tenant["tenant_id"])


@pytest.fixture(scope="module")
async def faber_acapy_client(faber_client: AsyncClient):
    # We extract the token from the x-api-key header as that's the easiest
    # method to create an AcaPyClient from an AsyncClient
    [_, token] = faber_client.headers.get("x-api-key").split(".", maxsplit=1)

    client = ecosystem_acapy_client(token=token)
    yield client

    await client.close()


@pytest.fixture(scope="module")
async def faber_and_alice_connection(
    alice_member_client: AsyncClient,
    faber_client: AsyncClient,
) -> FaberAliceConnect:
    # create invitation on faber side
    invitation = (
        await faber_client.post("/generic/connections/create-invitation")
    ).json()

    # accept invitation on alice side
    invitation_response = (
        await alice_member_client.post(
            "/generic/connections/accept-invitation",
            json={"invitation": invitation["invitation"]},
        )
    ).json()

    faber_connection_id = invitation["connection_id"]
    alice_connection_id = invitation_response["connection_id"]

    # fetch and validate
    # both connections should be active - we have waited long enough for events to be exchanged
    assert check_webhook_state(
        alice_member_client,
        topic="connections",
        filter_map={"state": "completed", "connection_id": alice_connection_id},
    )
    assert check_webhook_state(
        faber_client,
        topic="connections",
        filter_map={"state": "completed", "connection_id": faber_connection_id},
    )

    return {
        "alice_connection_id": alice_connection_id,
        "faber_connection_id": faber_connection_id,
    }
