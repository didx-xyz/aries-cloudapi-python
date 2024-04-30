from dataclasses import dataclass

import pytest

from app.models.tenants import CreateTenantResponse
from app.routes.connections import CreateInvitation
from app.routes.connections import router as conn_router
from app.routes.oob import router as oob_router
from app.services.trust_registry import actors
from app.services.trust_registry.actors import fetch_actor_by_id
from app.tests.util.webhooks import check_webhook_state
from app.util.string import base64_to_json
from shared import RichAsyncClient

OOB_BASE_PATH = oob_router.prefix
CONNECTIONS_BASE_PATH = conn_router.prefix


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
    json_request = CreateInvitation(
        alias="bob",
        multi_use=False,
        use_public_did=False,
    ).model_dump()
    invitation = (
        await bob_member_client.post(
            f"{CONNECTIONS_BASE_PATH}/create-invitation", json=json_request
        )
    ).json()

    # accept invitation on alice side
    invitation_response = (
        await alice_member_client.post(
            f"{CONNECTIONS_BASE_PATH}/accept-invitation",
            json={"alias": "alice", "invitation": invitation["invitation"]},
        )
    ).json()

    bob_connection_id = invitation["connection_id"]
    alice_connection_id = invitation_response["connection_id"]

    # fetch and validate
    # both connections should be active - we have waited long enough for events to be exchanged
    assert await check_webhook_state(
        alice_member_client,
        topic="connections",
        state="completed",
        look_back=5,
    )
    assert await check_webhook_state(
        bob_member_client,
        topic="connections",
        state="completed",
        look_back=5,
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
    request,
    alice_member_client: RichAsyncClient,
    alice_tenant: CreateTenantResponse,
    acme_client: RichAsyncClient,
    acme_verifier: CreateTenantResponse,
) -> AcmeAliceConnect:
    if hasattr(request, "param") and request.param == "trust_registry":
        acme_actor = await fetch_actor_by_id(acme_verifier.wallet_id)
        assert acme_actor["didcomm_invitation"]

        invitation = acme_actor["didcomm_invitation"]
        invitation_json = base64_to_json(invitation.split("?oob=")[1])

        # accept invitation on alice side
        invitation_response = (
            await alice_member_client.post(
                f"{OOB_BASE_PATH}/accept-invitation",
                json={"invitation": invitation_json},
            )
        ).json()

        alice_label = alice_tenant.wallet_label
        payload = await check_webhook_state(
            client=acme_client,
            topic="connections",
            state="completed",
            filter_map={
                "their_label": alice_label,
            },
        )

        alice_connection_id = invitation_response["connection_id"]
        acme_connection_id = payload["connection_id"]
    else:
        # create invitation on acme side
        invitation = (
            await acme_client.post(f"{CONNECTIONS_BASE_PATH}/create-invitation")
        ).json()

        # accept invitation on alice side
        invitation_response = (
            await alice_member_client.post(
                f"{CONNECTIONS_BASE_PATH}/accept-invitation",
                json={"invitation": invitation["invitation"]},
            )
        ).json()

        alice_connection_id = invitation_response["connection_id"]
        acme_connection_id = invitation["connection_id"]

    # fetch and validate - both connections should be active before continuing
    assert await check_webhook_state(
        alice_member_client,
        topic="connections",
        state="completed",
        filter_map={
            "connection_id": alice_connection_id,
        },
        look_back=5,
    )
    assert await check_webhook_state(
        acme_client,
        topic="connections",
        state="completed",
        filter_map={
            "connection_id": acme_connection_id,
        },
        look_back=5,
    )

    return AcmeAliceConnect(
        alice_connection_id=alice_connection_id,
        acme_connection_id=acme_connection_id,
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
        await faber_client.post(f"{CONNECTIONS_BASE_PATH}/create-invitation")
    ).json()

    # accept invitation on alice side
    invitation_response = (
        await alice_member_client.post(
            f"{CONNECTIONS_BASE_PATH}/accept-invitation",
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
        state="completed",
        filter_map={
            "connection_id": alice_connection_id,
        },
        look_back=5,
    )
    assert await check_webhook_state(
        faber_client,
        topic="connections",
        state="completed",
        filter_map={
            "connection_id": faber_connection_id,
        },
        look_back=5,
    )

    return FaberAliceConnect(
        alice_connection_id=alice_connection_id, faber_connection_id=faber_connection_id
    )


@dataclass
class MeldCoAliceConnect:
    alice_connection_id: str
    meld_co_connection_id: str


# Create fixture to handle parameters and return either meld_co-alice connection fixture
@pytest.fixture(scope="function")
async def meld_co_and_alice_connection(
    request,
    alice_tenant: CreateTenantResponse,
    alice_member_client: RichAsyncClient,
    meld_co_client: RichAsyncClient,
    meld_co_issuer_verifier: CreateTenantResponse,
) -> MeldCoAliceConnect:
    if hasattr(request, "param") and request.param == "trust_registry":
        # get invitation as on trust registry
        meld_co_label = meld_co_issuer_verifier.wallet_label

        actor_record = await actors.fetch_actor_by_name(meld_co_label)

        invitation = actor_record["didcomm_invitation"]
        invitation_json = base64_to_json(invitation.split("?oob=")[1])

        # accept invitation on alice side
        invitation_response = (
            await alice_member_client.post(
                f"{OOB_BASE_PATH}/accept-invitation",
                json={"invitation": invitation_json},
            )
        ).json()

        alice_label = alice_tenant.wallet_label
        payload = await check_webhook_state(
            client=meld_co_client,
            topic="connections",
            state="completed",
            filter_map={
                "their_label": alice_label,
            },
        )

        meld_co_connection_id = payload["connection_id"]
        alice_connection_id = invitation_response["connection_id"]
    else:
        # create invitation on meld_co side
        invitation = (
            await meld_co_client.post(f"{CONNECTIONS_BASE_PATH}/create-invitation")
        ).json()

        # accept invitation on alice side
        invitation_response = (
            await alice_member_client.post(
                f"{CONNECTIONS_BASE_PATH}/accept-invitation",
                json={"invitation": invitation["invitation"]},
            )
        ).json()

        meld_co_connection_id = invitation["connection_id"]
        alice_connection_id = invitation_response["connection_id"]

    # fetch and validate - both connections should be active before continuing
    assert await check_webhook_state(
        alice_member_client,
        topic="connections",
        state="completed",
        filter_map={
            "connection_id": alice_connection_id,
        },
        look_back=5,
    )
    assert await check_webhook_state(
        meld_co_client,
        topic="connections",
        state="completed",
        filter_map={
            "connection_id": meld_co_connection_id,
        },
        look_back=5,
    )

    return MeldCoAliceConnect(
        alice_connection_id=alice_connection_id,
        meld_co_connection_id=meld_co_connection_id,
    )
