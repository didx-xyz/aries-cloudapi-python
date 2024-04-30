from dataclasses import dataclass
from typing import Optional

from app.models.tenants import CreateTenantResponse
from app.routes.connections import CreateInvitation
from app.routes.connections import router as conn_router
from app.routes.oob import router as oob_router
from app.services.trust_registry.actors import fetch_actor_by_id
from app.tests.util.regression_testing import (
    RegressionTestConfig,
    TestMode,
    assert_fail_on_recreating_fixtures,
)
from app.tests.util.webhooks import check_webhook_state
from app.util.string import base64_to_json
from shared import RichAsyncClient
from shared.models.connection_record import Connection

OOB_BASE_PATH = oob_router.prefix
CONNECTIONS_BASE_PATH = conn_router.prefix


@dataclass
class BobAliceConnect:
    alice_connection_id: str
    bob_connection_id: str


@dataclass
class AcmeAliceConnect:
    alice_connection_id: str
    acme_connection_id: str


@dataclass
class FaberAliceConnect:
    alice_connection_id: str
    faber_connection_id: str


@dataclass
class MeldCoAliceConnect:
    alice_connection_id: str
    meld_co_connection_id: str


async def assert_both_connections_ready(
    member_client_1: RichAsyncClient,
    member_client_2: RichAsyncClient,
    connection_id_1: str,
    connection_id_2: str,
):
    assert await check_webhook_state(
        member_client_1,
        topic="connections",
        state="completed",
        filter_map={
            "connection_id": connection_id_1,
        },
        look_back=5,
    )
    assert await check_webhook_state(
        member_client_2,
        topic="connections",
        state="completed",
        filter_map={
            "connection_id": connection_id_2,
        },
        look_back=5,
    )


async def create_bob_alice_connection(
    alice_member_client: RichAsyncClient, bob_member_client: RichAsyncClient, alias: str
):
    # create invitation on bob side
    json_request = CreateInvitation(
        alias=alias,
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
            json={"alias": alias, "invitation": invitation["invitation"]},
        )
    ).json()

    bob_connection_id = invitation["connection_id"]
    alice_connection_id = invitation_response["connection_id"]

    # validate both connections should be active
    await assert_both_connections_ready(
        alice_member_client, bob_member_client, alice_connection_id, bob_connection_id
    )

    return BobAliceConnect(
        alice_connection_id=alice_connection_id, bob_connection_id=bob_connection_id
    )


async def fetch_existing_connection_by_alias(
    member_client: RichAsyncClient, alias: str, their_label: Optional[str] = None
) -> Optional[Connection]:
    list_connections_response = await member_client.get(
        f"{CONNECTIONS_BASE_PATH}",
        params={"alias": alias, "state": "completed"},
    )
    list_connections = list_connections_response.json()

    if their_label:  #  to handle Trust Registry invites, where alias in not unique
        list_connections = [
            connection
            for connection in list_connections
            if connection["their_label"] == their_label  # filter by their label
        ]

    num_connections = len(list_connections)
    assert (
        num_connections < 2
    ), f"Should have 1 or 0 connections with this alias, got: {num_connections}"

    if list_connections:
        return Connection.model_validate(list_connections[0])


async def fetch_or_create_connection(
    alice_member_client: RichAsyncClient,
    bob_member_client: RichAsyncClient,
    connection_alias: str,
) -> BobAliceConnect:
    # fetch connection with this alias for both bob and alice
    alice_connection = await fetch_existing_connection_by_alias(
        alice_member_client, connection_alias
    )

    bob_connection = await fetch_existing_connection_by_alias(
        bob_member_client, connection_alias
    )

    # Check if connections exist
    if alice_connection and bob_connection:
        return BobAliceConnect(
            alice_connection_id=alice_connection.connection_id,
            bob_connection_id=bob_connection.connection_id,
        )
    else:
        # Create connection since they don't exist
        assert_fail_on_recreating_fixtures()
        return await create_bob_alice_connection(
            alice_member_client,
            bob_member_client,
            alias=connection_alias,
        )


async def create_connection_by_test_mode(
    test_mode: str,
    alice_member_client: RichAsyncClient,
    bob_member_client: RichAsyncClient,
    alias: str,
) -> BobAliceConnect:
    if test_mode == TestMode.clean_run:
        return await create_bob_alice_connection(
            alice_member_client, bob_member_client, alias=alias
        )
    elif test_mode == TestMode.regression_run:
        connection_alias_prefix = RegressionTestConfig.reused_connection_alias

        return await fetch_or_create_connection(
            alice_member_client,
            bob_member_client,
            connection_alias=f"{connection_alias_prefix}-{alias}",
        )
    else:
        assert False, f"unknown test mode: {test_mode}"


async def connect_using_trust_registry_invite(
    alice_member_client: RichAsyncClient,
    alice_tenant: CreateTenantResponse,
    verifier_client: RichAsyncClient,
    verifier: CreateTenantResponse,
    connection_alias: str,
) -> AcmeAliceConnect:
    acme_actor = await fetch_actor_by_id(verifier.wallet_id)
    assert acme_actor["didcomm_invitation"]

    invitation = acme_actor["didcomm_invitation"]
    invitation_json = base64_to_json(invitation.split("?oob=")[1])

    # accept invitation on alice side -- she uses here connection alias
    invitation_response = (
        await alice_member_client.post(
            f"{OOB_BASE_PATH}/accept-invitation",
            json={"alias": connection_alias, "invitation": invitation_json},
        )
    ).json()

    alice_label = alice_tenant.wallet_label
    payload = await check_webhook_state(
        client=verifier_client,
        topic="connections",
        state="completed",
        filter_map={
            "their_label": alice_label,
        },
    )

    alice_connection_id = invitation_response["connection_id"]
    acme_connection_id = payload["connection_id"]

    # both connections should be active before continuing
    await assert_both_connections_ready(
        alice_member_client, verifier_client, alice_connection_id, acme_connection_id
    )

    return AcmeAliceConnect(
        alice_connection_id=alice_connection_id, acme_connection_id=acme_connection_id
    )


async def fetch_or_create_trust_registry_connection(
    alice_member_client: RichAsyncClient,
    alice_tenant: CreateTenantResponse,
    verifier_client: RichAsyncClient,
    verifier: CreateTenantResponse,
    connection_alias: str,
) -> AcmeAliceConnect:
    # fetch connection by alias for alice's side
    alice_connection = await fetch_existing_connection_by_alias(
        alice_member_client, alias=connection_alias
    )

    # The Trust Registry OOB invite has alias defined as:
    trust_registry_invite_alias = f"Trust Registry {verifier.wallet_label}"

    # Need to filter by their_label, as above alias is not necessarily unique
    alice_label = alice_tenant.wallet_label
    verifier_connection = await fetch_existing_connection_by_alias(
        verifier_client, alias=trust_registry_invite_alias, their_label=alice_label
    )

    # Check if connections exist
    if alice_connection and verifier_connection:
        return AcmeAliceConnect(
            alice_connection_id=alice_connection.connection_id,
            acme_connection_id=verifier_connection.connection_id,
        )
    else:
        # Create connection since they don't exist
        assert_fail_on_recreating_fixtures()
        return await connect_using_trust_registry_invite(
            alice_member_client=alice_member_client,
            alice_tenant=alice_tenant,
            verifier_client=verifier_client,
            verifier=verifier,
            connection_alias=connection_alias,
        )
