from typing import Any, Dict, TypedDict

import pytest
from aries_cloudcontroller import AcaPyClient

from app.generic.connections.connections import CreateInvitation
from app.generic.verifier.verifier_utils import ed25519_verkey_to_did_key
from app.tests.util.client import (
    get_tenant_acapy_client,
    get_tenant_admin_client,
    get_tenant_client,
)
from app.tests.util.ledger import create_public_did
from app.tests.util.tenants import (create_issuer_tenant, create_tenant,
                                    delete_tenant)
from app.tests.util.webhooks import check_webhook_state
from app.util.rich_async_client import RichAsyncClient


class BobAliceConnect(TypedDict):
    alice_connection_id: str
    bob_connection_id: str


class BobAlicePublicDid(TypedDict):
    bob_public_did: str
    alice_public_did: str


@pytest.fixture(scope="function")
async def bob_member_client():
    async with get_tenant_admin_client() as client:
        tenant = await create_issuer_tenant(client, "bob")

        bob_client = get_tenant_client(token=tenant["access_token"])
        yield bob_client

        await bob_client.aclose()

        await delete_tenant(client, tenant["tenant_id"])


@pytest.fixture(scope="function")
async def alice_tenant():
    async with get_tenant_admin_client() as client:
        tenant = await create_tenant(client, "alice")

        yield tenant

        await delete_tenant(client, tenant["tenant_id"])


@pytest.fixture(scope="function")
async def alice_member_client(alice_tenant: Any):
    alice_client = get_tenant_client(token=alice_tenant["access_token"])

    yield alice_client

    await alice_client.aclose()


@pytest.fixture(scope="function")
async def bob_acapy_client(bob_member_client: RichAsyncClient):
    # We extract the token from the x-api-key header as that's the easiest
    # method to create an AcaPyClient from an AsyncClient
    [_, token] = bob_member_client.headers.get(
        "x-api-key").split(".", maxsplit=1)

    client = get_tenant_acapy_client(token=token)
    yield client

    await client.close()


@pytest.fixture(scope="function")
async def alice_acapy_client(alice_member_client: RichAsyncClient):

    client = get_tenant_acapy_client(token=token)
    yield client

    await client.close()


@pytest.fixture(scope="function")
async def bob_and_alice_public_did(
    alice_acapy_client: AcaPyClient,
    bob_acapy_client: AcaPyClient,
) -> BobAlicePublicDid:

    bob_records = await bob_acapy_client.connection.get_connections()
    alice_records = await alice_acapy_client.connection.get_connections()

    await bob_acapy_client.connection.accept_invitation(
        conn_id=bob_records.results[-1].connection_id
    )
    await alice_acapy_client.connection.accept_invitation(
        conn_id=alice_records.results[-1].connection_id
    )

    bob_records = await bob_acapy_client.connection.get_connections()
    alice_records = await alice_acapy_client.connection.get_connections()

    bob_did = await create_public_did(bob_acapy_client)
    alice_did = await create_public_did(alice_acapy_client)

    if not bob_did.did or not alice_did.did:
        raise Exception("Missing public did for alice or bob")

    return {
        "bob_public_did": bob_did.did,
        "alice_public_did": alice_did.did,
    }


@pytest.fixture(scope="function")
async def bob_and_alice_connection(
    bob_member_client: RichAsyncClient,
    alice_member_client: RichAsyncClient,
) -> BobAliceConnect:
    # create invitation on bob side
    invitation = (
        await bob_member_client.post("/generic/connections/create-invitation")
    ).json()

    # accept invitation on alice side
    invitation_response = (
        await alice_member_client.post(
            "/generic/connections/accept-invitation",
            json={"invitation": invitation["invitation"]},
        )
    ).json()

    assert check_webhook_state(
        alice_member_client, topic="connections", filter_map={"state": "completed"}
    )

    bob_connection_id = invitation["connection_id"]
    alice_connection_id = invitation_response["connection_id"]

    # fetch and validate
    # both connections should be active - we have waited long enough for events to be exchanged
    assert check_webhook_state(
        alice_member_client,
        topic="connections",
        filter_map={"state": "completed"},
    )
    assert check_webhook_state(
        bob_member_client,
        topic="connections",
        filter_map={"state": "completed"},
    )
    # assert check_webhook_state(
    #     alice_member_client,
    #     topic="endorsements",
    #     filter_map={"state": "transaction-acked"},
    # )
    assert check_webhook_state(
        bob_member_client,
        topic="endorsements",
        filter_map={"state": "transaction-acked"},
    )

    return {
        "alice_connection_id": alice_connection_id,
        "bob_connection_id": bob_connection_id,
    }


class InvitationResultDict(TypedDict):
    invitation: Dict[str, Any]
    connection_id: str


class MultiInvite(TypedDict):
    multi_use_invitation: InvitationResultDict
    invitation_key: str
    did_from_rec_key: str


@pytest.fixture(scope="function")
async def bob_multi_use_invitation(
    bob_member_client: RichAsyncClient,
) -> MultiInvite:
    create_invite_json = CreateInvitation(
        alias=None,
        multi_use=True,
        use_public_did=False,
    ).dict()
    # Create a multi-use invitation
    invitation = (
        await bob_member_client.post(
            "/generic/connections/create-invitation",
            json=create_invite_json,
        )
    ).json()

    recipient_key = invitation["invitation"]["recipientKeys"][0]
    bob_multi_invite = MultiInvite(
        multi_use_invitation=invitation,
        invitation_key=recipient_key,
        did_from_rec_key=ed25519_verkey_to_did_key(key=recipient_key),
    )

    return bob_multi_invite


@pytest.fixture(scope="function")
async def alice_bob_connect_multi(
    bob_member_client: RichAsyncClient,
    alice_member_client: RichAsyncClient,
    bob_multi_use_invitation: MultiInvite,
) -> BobAliceConnect:
    invitation = bob_multi_use_invitation["multi_use_invitation"]["invitation"]

    # accept invitation on alice side
    invitation_response = (
        await alice_member_client.post(
            "/generic/connections/accept-invitation",
            json={"invitation": invitation},
        )
    ).json()

    assert check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "request-sent"},
        topic="connections",
        max_duration=60,
    )

    bob_connection_id = bob_multi_use_invitation["multi_use_invitation"][
        "connection_id"
    ]
    alice_connection_id = invitation_response["connection_id"]

    # fetch and validate
    # both connections should be active - we have waited long enough for events to be exchanged
    bob_connection_records = (
        await bob_member_client.get("/generic/connections")
    ).json()

    bob_connection_id = bob_connection_records[0]["connection_id"]

    assert check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "completed"},
        topic="connections",
        max_duration=120,
    )
    assert check_webhook_state(
        client=bob_member_client,
        filter_map={"state": "completed"},
        topic="connections",
        max_duration=120,
    )

    return {
        "alice_connection_id": alice_connection_id,
        "bob_connection_id": bob_connection_id,
    }
