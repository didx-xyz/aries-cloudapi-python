from typing import Any, TypedDict

import pytest
from httpx import AsyncClient

from app.facades.trust_registry import actor_by_id
from app.listener import Listener
from app.tests.util.client import (tenant_acapy_client, tenant_admin_client,
                                   tenant_client)
from app.tests.util.string import base64_to_json
from app.tests.util.tenants import (create_issuer_tenant,
                                    create_verifier_tenant, delete_tenant)
from app.tests.util.webhooks import check_webhook_state


class FaberAliceConnect(TypedDict):
    faber_connection_id: str
    alice_connection_id: str


class AcmeAliceConnect(TypedDict):
    acme_connection_id: str
    alice_connection_id: str


@pytest.fixture(scope="function")
async def faber_client():
    async with tenant_admin_client() as client:
        tenant = await create_issuer_tenant(client, "faber")

        if "access_token" not in tenant:
            raise Exception(f"Error creating tenant: {tenant}")

        faber_async_client = tenant_client(token=tenant["access_token"])
        yield faber_async_client

        await faber_async_client.aclose()

        await delete_tenant(client, tenant["tenant_id"])


@pytest.fixture(scope="function")
async def faber_acapy_client(faber_client: AsyncClient):
    # We extract the token from the x-api-key header as that's the easiest
    # method to create an AcaPyClient from an AsyncClient
    [_, token] = faber_client.headers.get("x-api-key").split(".", maxsplit=1)

    client = tenant_acapy_client(token=token)
    yield client

    await client.close()


@pytest.fixture(scope="function")
async def acme_tenant():
    async with tenant_admin_client() as client:
        tenant = await create_verifier_tenant(client, "acme")

        if "access_token" not in tenant:
            raise Exception(f"Error creating tenant: {tenant}")

        yield tenant

        await delete_tenant(client, tenant["tenant_id"])


@pytest.fixture(scope="function")
async def acme_client(acme_tenant: Any):
    acme_async_client = tenant_client(token=acme_tenant["access_token"])
    yield acme_async_client

    await acme_async_client.aclose()


@pytest.fixture(scope="function")
async def acme_acapy_client(faber_client: AsyncClient):
    # We extract the token from the x-api-key header as that's the easiest
    # method to create an AcaPyClient from an AsyncClient
    [_, token] = faber_client.headers.get("x-api-key").split(".", maxsplit=1)

    client = tenant_acapy_client(token=token)
    yield client

    await client.close()


@pytest.fixture(scope="function")
async def acme_and_alice_connection(
    alice_member_client: AsyncClient, acme_tenant: Any
) -> AcmeAliceConnect:

    acme_actor = await actor_by_id(acme_tenant["tenant_id"])

    assert acme_actor
    assert acme_actor["didcomm_invitation"]

    invitation_json = base64_to_json(
        acme_actor["didcomm_invitation"].split("?oob=")[1])

    listener = Listener(topic="connections",
                        wallet_id=acme_tenant["tenant_id"])

    # accept invitation on alice side
    invitation_response = (
        await alice_member_client.post(
            "/generic/oob/accept-invitation",
            json={"invitation": invitation_json},
        )
    ).json()

    payload = await listener.wait_for_filtered_event(filter_map={"state": "completed"})
    listener.stop()

    acme_connection_id = payload["connection_id"]
    alice_connection_id = invitation_response["connection_id"]

    return {
        "alice_connection_id": alice_connection_id,
        "acme_connection_id": acme_connection_id,
    }


@pytest.fixture(scope="function")
async def faber_and_alice_connection(
    alice_member_client: AsyncClient, faber_client: AsyncClient, alice_tenant: Any
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
        filter_map={"state": "completed",
                    "connection_id": alice_connection_id},
    )
    assert check_webhook_state(
        faber_client,
        topic="connections",
        filter_map={"state": "completed",
                    "connection_id": faber_connection_id},
    )

    return {
        "alice_connection_id": alice_connection_id,
        "faber_connection_id": faber_connection_id,
    }
