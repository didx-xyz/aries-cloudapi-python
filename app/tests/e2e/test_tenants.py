from uuid import uuid4

import pytest
from aries_cloudcontroller.acapy_client import AcaPyClient
from assertpy.assertpy import assert_that
from fastapi import HTTPException

import app.services.trust_registry.actors as trust_registry
from app.dependencies.acapy_clients import get_tenant_controller
from app.routes.admin.tenants import router
from app.services import acapy_wallet
from app.tests.util.client import get_tenant_client
from app.tests.util.webhooks import check_webhook_state
from app.util.did import ed25519_verkey_to_did_key
from shared import RichAsyncClient

TENANTS_BASE_PATH = router.prefix


@pytest.mark.anyio
async def test_get_wallet_auth_token(tenant_admin_client: RichAsyncClient):
    response = await tenant_admin_client.post(
        TENANTS_BASE_PATH,
        json={
            "image_url": "https://image.ca",
            "wallet_label": uuid4().hex,
            "roles": ["verifier"],
            "group_id": "TestGroup",
        },
    )

    assert response.status_code == 200

    tenant = response.json()
    wallet_id = tenant["wallet_id"]

    response = await tenant_admin_client.get(
        f"{TENANTS_BASE_PATH}/{wallet_id}/access-token"
    )
    assert response.status_code == 200

    token = response.json()

    assert token["access_token"]
    assert token["access_token"].startswith("tenant.ey")


@pytest.mark.anyio
async def test_create_tenant_member_wo_wallet_name(
    tenant_admin_client: RichAsyncClient, tenant_admin_acapy_client: AcaPyClient
):
    wallet_label = uuid4().hex
    group_id = "TestGroup"
    response = await tenant_admin_client.post(
        TENANTS_BASE_PATH,
        json={
            "image_url": "https://image.ca",
            "wallet_label": wallet_label,
            "group_id": group_id,
        },
    )

    assert response.status_code == 200

    tenant = response.json()

    wallet = await tenant_admin_acapy_client.multitenancy.get_wallet(
        wallet_id=tenant["wallet_id"]
    )

    wallet_name = wallet.settings["wallet.name"]
    assert tenant["wallet_id"] == wallet.wallet_id
    assert tenant["group_id"] == group_id
    assert tenant["wallet_label"] == wallet_label
    assert tenant["created_at"] == wallet.created_at
    assert tenant["updated_at"] == wallet.updated_at
    assert tenant["wallet_name"] == wallet_name
    assert_that(wallet_name).is_length(32)


@pytest.mark.anyio
async def test_create_tenant_member_w_wallet_name(
    tenant_admin_client: RichAsyncClient, tenant_admin_acapy_client: AcaPyClient
):
    wallet_label = uuid4().hex
    wallet_name = "TestWalletName"
    group_id = "TestGroup"
    create_tenant_payload = {
        "image_url": "https://image.ca",
        "wallet_label": wallet_label,
        "group_id": group_id,
        "wallet_name": wallet_name,
    }

    response = await tenant_admin_client.post(
        TENANTS_BASE_PATH,
        json=create_tenant_payload,
    )

    assert response.status_code == 200

    tenant = response.json()

    wallet = await tenant_admin_acapy_client.multitenancy.get_wallet(
        wallet_id=tenant["wallet_id"]
    )

    assert tenant["wallet_id"] == wallet.wallet_id
    assert tenant["group_id"] == group_id
    assert tenant["wallet_label"] == wallet_label
    assert tenant["created_at"] == wallet.created_at
    assert tenant["updated_at"] == wallet.updated_at
    assert tenant["wallet_name"] == wallet_name
    assert wallet.settings["wallet.name"] == wallet_name

    with pytest.raises(HTTPException) as http_error:
        await tenant_admin_client.post(
            TENANTS_BASE_PATH,
            json=create_tenant_payload,
        )
    assert http_error.value.status_code == 409
    assert "already exists" in http_error.value.detail


@pytest.mark.anyio
async def test_create_tenant_issuer(
    tenant_admin_client: RichAsyncClient,
    tenant_admin_acapy_client: AcaPyClient,
    governance_acapy_client: AcaPyClient,
):
    wallet_label = uuid4().hex
    group_id = "TestGroup"
    response = await tenant_admin_client.post(
        TENANTS_BASE_PATH,
        json={
            "image_url": "https://image.ca",
            "wallet_label": wallet_label,
            "roles": ["issuer"],
            "group_id": group_id,
        },
    )
    assert response.status_code == 200

    tenant = response.json()
    wallet_id = tenant["wallet_id"]

    wallet = await tenant_admin_acapy_client.multitenancy.get_wallet(
        wallet_id=wallet_id
    )

    acapy_token: str = tenant["access_token"].split(".", 1)[1]
    actor = await trust_registry.fetch_actor_by_id(wallet_id)

    endorser_did = await acapy_wallet.get_public_did(governance_acapy_client)

    async with get_tenant_controller(acapy_token) as tenant_controller:
        public_did = await acapy_wallet.get_public_did(tenant_controller)

        connections = await tenant_controller.connection.get_connections()

        connections = [
            connection
            for connection in connections.results
            if connection.their_public_did == endorser_did.did
        ]

    if not actor:
        raise Exception("Missing actor")

    connection = connections[0]

    async with get_tenant_client(token=tenant["access_token"]) as client:
        # Wait for connection to be completed
        assert await check_webhook_state(
            client=client,
            topic="connections",
            filter_map={
                "state": "completed",
                "connection_id": connection.connection_id,
            },
        )

    # Actor
    assert_that(actor).has_name(tenant["wallet_label"])
    assert_that(actor).has_did(f"did:sov:{public_did.did}")
    assert_that(actor).has_roles(["issuer"])

    # Connection with endorser
    assert_that(connection).has_their_public_did(endorser_did.did)

    # Tenant
    assert_that(tenant).has_wallet_id(wallet.wallet_id)
    assert_that(tenant).has_wallet_label(wallet_label)
    assert_that(tenant).has_created_at(wallet.created_at)
    assert_that(tenant).has_updated_at(wallet.updated_at)
    assert_that(wallet.settings["wallet.name"]).is_length(32)

    with pytest.raises(HTTPException) as http_error:
        await tenant_admin_client.post(
            TENANTS_BASE_PATH,
            json={
                "image_url": "https://image.ca",
                "wallet_label": wallet_label,
                "roles": ["issuer"],
                "group_id": group_id,
            },
        )

        assert http_error.status_code == 409
        assert "Can't create Tenant. Actor with name:" in http_error.json()["details"]


@pytest.mark.anyio
async def test_create_tenant_verifier(
    tenant_admin_client: RichAsyncClient, tenant_admin_acapy_client: AcaPyClient
):
    wallet_label = uuid4().hex
    response = await tenant_admin_client.post(
        TENANTS_BASE_PATH,
        json={
            "image_url": "https://image.ca",
            "wallet_label": wallet_label,
            "roles": ["verifier"],
        },
    )
    assert response.status_code == 200

    tenant = response.json()
    wallet_id = tenant["wallet_id"]

    wallet = await tenant_admin_acapy_client.multitenancy.get_wallet(
        wallet_id=wallet_id
    )

    actor = await trust_registry.fetch_actor_by_id(wallet_id)

    if not actor:
        raise Exception("Missing actor")

    acapy_token: str = tenant["access_token"].split(".", 1)[1]

    async with get_tenant_controller(acapy_token) as tenant_controller:
        connections = await tenant_controller.connection.get_connections(
            alias=f"Trust Registry {wallet_label}"
        )

    connection = connections.results[0]

    # Connection invitation
    assert_that(connection).has_state("invitation")

    assert_that(actor).has_name(tenant["wallet_label"])
    assert_that(actor).has_did(ed25519_verkey_to_did_key(connection.invitation_key))
    assert_that(actor).has_roles(["verifier"])

    # Tenant
    assert_that(tenant).has_wallet_id(wallet.wallet_id)
    assert_that(tenant).has_wallet_label(wallet_label)
    assert_that(tenant).has_created_at(wallet.created_at)
    assert_that(tenant).has_updated_at(wallet.updated_at)
    assert_that(wallet.settings["wallet.name"]).is_length(32)


@pytest.mark.anyio
async def test_update_tenant_verifier_to_issuer(
    tenant_admin_client: RichAsyncClient,
    tenant_admin_acapy_client: AcaPyClient,
    governance_acapy_client: AcaPyClient,
):
    wallet_label = uuid4().hex
    image_url = "https://image.ca"
    response = await tenant_admin_client.post(
        TENANTS_BASE_PATH,
        json={
            "image_url": image_url,
            "wallet_label": wallet_label,
            "roles": ["verifier"],
        },
    )

    verifier_tenant = response.json()
    verifier_wallet_id = verifier_tenant["wallet_id"]
    verifier_actor = await trust_registry.fetch_actor_by_id(verifier_wallet_id)
    assert verifier_actor
    assert_that(verifier_actor).has_name(wallet_label)
    assert_that(verifier_actor).has_roles(["verifier"])

    wallet = await tenant_admin_acapy_client.multitenancy.get_wallet(
        wallet_id=verifier_wallet_id
    )
    assert_that(wallet.settings["wallet.name"]).is_length(32)

    acapy_token: str = verifier_tenant["access_token"].split(".", 1)[1]

    async with get_tenant_controller(acapy_token) as tenant_controller:
        connections = await tenant_controller.connection.get_connections(
            alias=f"Trust Registry {wallet_label}"
        )

    connection = connections.results[0]

    # Connection invitation
    assert_that(connection).has_state("invitation")
    assert_that(verifier_actor).has_did(
        ed25519_verkey_to_did_key(connection.invitation_key)
    )

    # Tenant
    assert_that(verifier_tenant).has_wallet_id(wallet.wallet_id)
    assert_that(verifier_tenant).has_image_url(image_url)
    assert_that(verifier_tenant).has_wallet_label(wallet_label)
    assert_that(verifier_tenant).has_created_at(wallet.created_at)
    assert_that(verifier_tenant).has_updated_at(wallet.updated_at)

    new_wallet_label = uuid4().hex
    new_image_url = "https://some-ssi-site.org/image.png"
    new_roles = ["issuer", "verifier"]

    response = await tenant_admin_client.put(
        f"{TENANTS_BASE_PATH}/{verifier_wallet_id}",
        json={
            "image_url": new_image_url,
            "wallet_label": new_wallet_label,
            "roles": new_roles,
        },
    )
    new_tenant = response.json()
    assert_that(new_tenant).has_wallet_id(wallet.wallet_id)
    assert_that(new_tenant).has_image_url(new_image_url)
    assert_that(new_tenant).has_wallet_label(new_wallet_label)
    assert_that(new_tenant).has_created_at(wallet.created_at)

    new_actor = await trust_registry.fetch_actor_by_id(verifier_wallet_id)

    endorser_did = await acapy_wallet.get_public_did(governance_acapy_client)

    acapy_token = (
        (
            await tenant_admin_client.get(
                f"{TENANTS_BASE_PATH}/{verifier_wallet_id}/access-token"
            )
        )
        .json()["access_token"]
        .split(".", 1)[1]
    )

    async with get_tenant_controller(acapy_token) as tenant_controller:
        public_did = await acapy_wallet.get_public_did(tenant_controller)
        assert public_did

        _connections = (await tenant_controller.connection.get_connections()).results

        connections = [
            connection
            for connection in _connections
            if connection.their_public_did == endorser_did.did
        ]

    endorser_connection = connections[0]

    async with get_tenant_client(token=verifier_tenant["access_token"]) as client:
        # Wait for connection to be completed
        assert await check_webhook_state(
            client=client,
            topic="connections",
            filter_map={
                "state": "completed",
                "connection_id": endorser_connection.connection_id,
            },
        )

    # Connection invitation
    assert_that(endorser_connection).has_their_public_did(endorser_did.did)

    assert new_actor
    assert_that(new_actor).has_name(new_wallet_label)
    assert_that(new_actor).has_did(f"{new_actor['did']}")
    assert_that(new_actor["roles"]).contains_only("issuer", "verifier")

    assert new_actor["didcomm_invitation"] is not None


@pytest.mark.anyio
async def test_get_tenants(tenant_admin_client: RichAsyncClient):
    response = await tenant_admin_client.post(
        TENANTS_BASE_PATH,
        json={
            "image_url": "https://image.ca",
            "wallet_label": uuid4().hex,
            "roles": ["verifier"],
        },
    )

    assert response.status_code == 200
    created_tenant = response.json()
    first_wallet_id = created_tenant["wallet_id"]

    response = await tenant_admin_client.get(f"{TENANTS_BASE_PATH}/{first_wallet_id}")

    assert response.status_code == 200
    retrieved_tenant = response.json()
    created_tenant.pop("access_token")
    assert created_tenant == retrieved_tenant

    response = await tenant_admin_client.post(
        TENANTS_BASE_PATH,
        json={
            "image_url": "https://image.ca",
            "wallet_label": uuid4().hex,
            "roles": ["verifier"],
            "group_id": "ac/dc",
        },
    )

    assert response.status_code == 200
    last_wallet_id = response.json()["wallet_id"]

    response = await tenant_admin_client.get(TENANTS_BASE_PATH)
    assert response.status_code == 200
    tenants = response.json()
    assert len(tenants) >= 1

    # Make sure created tenant is returned
    assert_that(tenants).extracting("wallet_id").contains(last_wallet_id)
    assert_that(tenants).extracting("group_id").contains("ac/dc")


@pytest.mark.anyio
async def test_get_tenants_by_group(tenant_admin_client: RichAsyncClient):
    wallet_label = uuid4().hex
    group_id = "backstreetboys"
    response = await tenant_admin_client.post(
        TENANTS_BASE_PATH,
        json={
            "image_url": "https://image.ca",
            "wallet_label": wallet_label,
            "roles": ["verifier"],
            "group_id": group_id,
        },
    )

    assert response.status_code == 200
    created_tenant = response.json()
    wallet_id = created_tenant["wallet_id"]

    response = await tenant_admin_client.get(f"{TENANTS_BASE_PATH}?group_id={group_id}")
    assert response.status_code == 200
    tenants = response.json()
    assert len(tenants) >= 1

    # Make sure created tenant is returned
    assert_that(tenants).extracting("wallet_id").contains(wallet_id)
    assert_that(tenants).extracting("group_id").contains(group_id)

    response = await tenant_admin_client.get(f"{TENANTS_BASE_PATH}?group_id=spicegirls")
    assert response.status_code == 200
    tenants = response.json()
    assert len(tenants) == 0
    assert tenants == []


@pytest.mark.anyio
async def test_delete_tenant(
    tenant_admin_client: RichAsyncClient, tenant_admin_acapy_client: AcaPyClient
):
    wallet_label = uuid4().hex
    response = await tenant_admin_client.post(
        TENANTS_BASE_PATH,
        json={
            "image_url": "https://image.ca",
            "wallet_label": wallet_label,
            "roles": ["verifier"],
        },
    )

    assert response.status_code == 200
    tenant = response.json()
    wallet_id = tenant["wallet_id"]

    # Actor exists
    actor = await trust_registry.fetch_actor_by_id(wallet_id)
    assert actor

    response = await tenant_admin_client.delete(f"{TENANTS_BASE_PATH}/{wallet_id}")
    assert response.status_code == 200

    # Actor doesn't exist anymore
    actor = await trust_registry.fetch_actor_by_id(wallet_id)
    assert not actor

    with pytest.raises(Exception):
        await tenant_admin_acapy_client.multitenancy.get_wallet(wallet_id=wallet_id)
