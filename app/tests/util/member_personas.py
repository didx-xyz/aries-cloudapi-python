from typing import TypedDict
from random import random
import time
import json

import pytest
from assertpy import assert_that
from aries_cloudcontroller import (
    AcaPyClient,
    SchemaSendResult,
    InvitationResult,
)
from shared_models import (
    CredentialExchange,
)
from app.tests.util.trust_registry import register_issuer
from httpx import AsyncClient
from app.facades.trust_registry import (
    Actor,
    registry_has_schema,
    actor_by_did,
    register_schema,
    register_actor,
)
from app.generic.connections.connections import CreateInvitation
from app.generic.verifier.verifier_utils import ed25519_verkey_to_did_key

from app.tests.util.client import (
    member_acapy_client,
    yoma_client,
    member_admin_client,
    member_client,
)
from app.tests.util.ledger import create_public_did

from .tenants import create_tenant, delete_tenant
from app.tests.util.webhooks import check_webhook_state


class BobAliceConnect(TypedDict):
    alice_connection_id: str
    bob_connection_id: str


class BobAlicePublicDid(TypedDict):
    bob_public_did: str
    alice_public_did: str


class MultiInvite(TypedDict):
    multi_use_invitation: InvitationResult
    invitation_key: str
    did_from_rec_key: str


@pytest.fixture(scope="module")
async def bob_member_client():
    async with member_admin_client() as client:
        tenant = await create_tenant(client, "bob")

        yield member_client(token=tenant["access_token"])

        await delete_tenant(client, tenant["tenant_id"])


@pytest.fixture(scope="module")
async def alice_member_client():
    async with member_admin_client() as client:
        tenant = await create_tenant(client, "alice")

        yield member_client(token=tenant["access_token"])

        await delete_tenant(client, tenant["tenant_id"])


@pytest.fixture(scope="module")
async def bob_acapy_client(bob_member_client: AsyncClient):
    # We extract the token from the x-api-key header as that's the easiest
    # method to create an AcaPyClient from an AsyncClient
    [_, token] = bob_member_client.headers.get("x-api-key").split(".", maxsplit=1)

    client = member_acapy_client(token=token)
    yield client

    await client.close()


@pytest.fixture(scope="module")
async def alice_acapy_client(alice_member_client: AsyncClient):
    [_, token] = alice_member_client.headers.get("x-api-key").split(".", maxsplit=1)

    client = member_acapy_client(token=token)
    yield client

    await client.close()


@pytest.fixture(scope="module")
async def bob_and_alice_public_did(
    alice_acapy_client: AcaPyClient,
    bob_acapy_client: AcaPyClient,
) -> BobAlicePublicDid:
    bob_did = await create_public_did(bob_acapy_client)
    alice_did = await create_public_did(alice_acapy_client)

    return {
        "bob_public_did": bob_did.did,
        "alice_public_did": alice_did.did,
    }


@pytest.fixture(scope="module")
async def bob_multi_use_invitation(
    bob_member_client: AsyncClient,
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
    print(invitation)

    recipient_key = invitation["invitation"]["recipientKeys"][0]
    bob_multi_invite = MultiInvite(
        multi_use_invitation=invitation,
        invitation_key=recipient_key,
        did_from_rec_key=ed25519_verkey_to_did_key(key=recipient_key),
    )

    return bob_multi_invite


@pytest.fixture(scope="module")
async def register_bob_multi(
    bob_multi_use_invitation, schema_definition
) -> MultiInvite:

    if not await registry_has_schema(schema_id=schema_definition.schema_id):
        await register_schema(schema_definition.schema_id)

    if not await actor_by_did(did=bob_multi_use_invitation["did_from_rec_key"]):
        rand = random()
        await register_actor(
            Actor(
                id=f"test-actor-{rand}",
                name=f"Test Actor-{rand}",
                roles=["verifier"],
                did=bob_multi_use_invitation["did_from_rec_key"],
                didcomm_invitation=str(
                    bob_multi_use_invitation["multi_use_invitation"]["invitation"]
                ),
            )
        )
    return bob_multi_use_invitation


@pytest.fixture(scope="module")
async def issue_credential_to_bob(
    bob_member_client: AsyncClient,
    register_bob_multi: MultiInvite,
    yoma_client: AcaPyClient,
    schema_definition: SchemaSendResult,
) -> CredentialExchange:

    await register_issuer(yoma_client, schema_definition.schema_id)

    # Create a conenction from yoma to bob
    invitation_response = (
        await yoma_client.post(
            "/generic/connections/accept-invitation",
            json={
                "invitation": register_bob_multi["multi_use_invitation"]["invitation"]
            },
        )
    ).json()

    bob_connection_records = (
        await bob_member_client.get(f"/generic/connections")
    ).json()
    print(json.dumps(bob_connection_records, indent=2))

    bob_connection_id = bob_connection_records[0]["connection_id"]

    # send a credential to bob

    response = await bob_member_client.get(
        "/generic/issuer/credentials",
        params={"connection_id": bob_connection_id},
    )
    records = response.json()

    # nothing currently in bob's records
    assert len(records) == 0

    credential = {
        "protocol_version": "v1",
        "connection_id": invitation_response["connection_id"],
        "schema_id": schema_definition.schema_id,
        "attributes": {"speed": "average"},
    }

    # create and send credential offer- issuer
    response = await yoma_client.post(
        "/generic/issuer/credentials",
        json=credential,
    )
    response.raise_for_status()
    response = response.json()

    time.sleep(5)

    # get cred offer record - holder
    response = await bob_member_client.get("/generic/issuer/credentials")
    records = response.json()
    cred_id = records[0]["credential_id"]

    # send credential request - holder
    response = await bob_member_client.post(
        f"/generic/issuer/credentials/{cred_id}/request", json={}
    )

    # send credential - issuer
    response = await yoma_client.post(
        "/generic/issuer/credentials",
        json=credential,
    )
    response.raise_for_status()

    time.sleep(5)

    # response = await bob_member_client.get("/generic/issuer/credentials")
    # records = response.json()
    # cred_id = records[0]["credential_id"]
    # store credential - holder
    response = await bob_member_client.post(
        f"/generic/issuer/credentials/{cred_id}/store", json={}
    )
    return response.json()


@pytest.fixture(scope="module")
async def alice_bob_connect_multi(
    bob_member_client,
    alice_member_client,
    bob_multi_use_invitation,
) -> BobAliceConnect:
    invitation = bob_multi_use_invitation["multi_use_invitation"]["invitation"]

    # accept invitation on alice side
    invitation_response = (
        await alice_member_client.post(
            "/generic/connections/accept-invitation",
            json={"invitation": invitation},
        )
    ).json()

    print(f"\n\n\n\n Invitation: {invitation}\n\n\n")
    time.sleep(10)

    bob_connection_id = bob_multi_use_invitation["multi_use_invitation"][
        "connection_id"
    ]
    alice_connection_id = invitation_response["connection_id"]

    # fetch and validate
    # both connections should be active - we have waited long enough for events to be exchanged
    bob_connection_records = (
        await bob_member_client.get(f"/generic/connections")
    ).json()
    print(json.dumps(bob_connection_records, indent=2))

    bob_connection = bob_connection_records[0]
    bob_connection_id = bob_connection_records[0]["connection_id"]
    alice_connection = (
        await alice_member_client.get(f"/generic/connections/{alice_connection_id}")
    ).json()
    conn = {
        "alice_connection_id": alice_connection_id,
        "bob_connection_id": bob_connection_id,
    }
    print(conn)

    assert_that(bob_connection).has_state("completed")
    assert_that(alice_connection).has_state("completed")

    return {
        "alice_connection_id": alice_connection_id,
        "bob_connection_id": bob_connection_id,
    }


@pytest.fixture(scope="module")
async def bob_and_alice_connection(
    bob_member_client: AsyncClient,
    alice_member_client: AsyncClient,
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

    return {
        "alice_connection_id": alice_connection_id,
        "bob_connection_id": bob_connection_id,
    }
