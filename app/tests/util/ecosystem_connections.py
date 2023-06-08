from dataclasses import dataclass
from typing import Any, Dict, TypedDict

import pytest
from aries_cloudcontroller import AcaPyClient

from app.admin.tenants.models import CreateTenantResponse
from app.event_handling.sse_listener import SseListener
from app.facades.trust_registry import actor_by_id
from app.generic.connections.connections import CreateInvitation
from app.generic.verifier.verifier_utils import ed25519_verkey_to_did_key
from app.tests.util.ledger import create_public_did
from app.tests.util.string import base64_to_json
from app.tests.util.webhooks import check_webhook_state
from shared import RichAsyncClient


@dataclass
class BobAliceConnect:
    alice_connection_id: str
    bob_connection_id: str


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

    assert await check_webhook_state(
        alice_member_client, topic="connections", filter_map={"state": "completed"}
    )

    bob_connection_id = invitation["connection_id"]
    alice_connection_id = invitation_response["connection_id"]

    # fetch and validate
    # both connections should be active - we have waited long enough for events to be exchanged
    assert await check_webhook_state(
        alice_member_client,
        topic="connections",
        filter_map={"state": "completed"},
    )
    assert await check_webhook_state(
        bob_member_client,
        topic="connections",
        filter_map={"state": "completed"},
    )
    assert await check_webhook_state(
        bob_member_client,
        topic="endorsements",
        filter_map={"state": "transaction-acked"},
    )

    return BobAliceConnect(
        alice_connection_id=alice_connection_id, bob_connection_id=bob_connection_id
    )


@dataclass
class AcmeAliceConnect:
    alice_connection_id: str
    acme_connection_id: str


@pytest.fixture(scope="function")
async def acme_and_alice_connection(
    alice_member_client: RichAsyncClient, acme_verifier: CreateTenantResponse
) -> AcmeAliceConnect:
    acme_actor = await actor_by_id(acme_verifier.tenant_id)
    assert acme_actor["didcomm_invitation"]

    invitation_json = base64_to_json(acme_actor["didcomm_invitation"].split("?oob=")[1])

    acme_listener = SseListener(topic="connections", wallet_id=acme_verifier.tenant_id)

    # accept invitation on alice side
    invitation_response = (
        await alice_member_client.post(
            "/generic/oob/accept-invitation",
            json={"invitation": invitation_json},
        )
    ).json()

    payload = await acme_listener.wait_for_state(desired_state="completed")

    acme_connection_id = payload["connection_id"]
    alice_connection_id = invitation_response["connection_id"]

    return AcmeAliceConnect(
        alice_connection_id=alice_connection_id, acme_connection_id=acme_connection_id
    )


@dataclass
class FaberAliceConnect:
    alice_connection_id: str
    faber_connection_id: str


@pytest.fixture(scope="function")
async def faber_and_alice_connection(
    alice_member_client: RichAsyncClient, faber_client: RichAsyncClient
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
    assert await check_webhook_state(
        alice_member_client,
        topic="connections",
        filter_map={"state": "completed", "connection_id": alice_connection_id},
    )
    assert await check_webhook_state(
        faber_client,
        topic="connections",
        filter_map={"state": "completed", "connection_id": faber_connection_id},
    )

    return FaberAliceConnect(
        alice_connection_id=alice_connection_id, faber_connection_id=faber_connection_id
    )


@dataclass
class BobAlicePublicDid:
    alice_public_did: str
    bob_public_did: str


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

    return BobAlicePublicDid(alice_public_did=alice_did, bob_public_did=bob_did)


class InvitationResultDict(TypedDict):
    invitation: Dict[str, Any]
    connection_id: str


class MultiInvite(TypedDict):
    multi_use_invitation: InvitationResultDict
    invitation_key: str
    did_from_rec_key: str


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
) -> BobAliceConnect:
    multi_use_invite = bob_multi_use_invitation(bob_member_client)
    invitation = multi_use_invite["multi_use_invitation"]["invitation"]

    # accept invitation on alice side
    invitation_response = (
        await alice_member_client.post(
            "/generic/connections/accept-invitation",
            json={"invitation": invitation},
        )
    ).json()

    assert await check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "request-sent"},
        topic="connections",
        max_duration=60,
    )

    bob_connection_id = multi_use_invite["multi_use_invitation"]["connection_id"]
    alice_connection_id = invitation_response["connection_id"]

    # fetch and validate
    # both connections should be active - we have waited long enough for events to be exchanged
    bob_connection_records = (
        await bob_member_client.get("/generic/connections")
    ).json()

    bob_connection_id = bob_connection_records[0]["connection_id"]

    assert await check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "completed"},
        topic="connections",
        max_duration=120,
    )
    assert await check_webhook_state(
        client=bob_member_client,
        filter_map={"state": "completed"},
        topic="connections",
        max_duration=120,
    )

    return BobAliceConnect(
        alice_connection_id=alice_connection_id, bob_connection_id=bob_connection_id
    )
