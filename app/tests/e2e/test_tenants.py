from uuid import uuid4

import pytest
from aries_cloudcontroller.acapy_client import AcaPyClient
from assertpy.assertpy import assert_that

from app.admin.tenants import tenants
from app.facades import acapy_wallet, trust_registry
from app.role import Role
from app.tests.util.client import get_tenant_client
from app.tests.util.webhooks import check_webhook_state
from app.util.did import ed25519_verkey_to_did_key
from shared import RichAsyncClient
from shared.dependencies.auth import get_tenant_controller

BASE_PATH = tenants.router.prefix


@pytest.mark.anyio
async def test_get_tenant_auth_token(tenant_admin_client: RichAsyncClient):
    response = await tenant_admin_client.post(
        BASE_PATH,
        json={
            "image_url": "https://image.ca",
            "name": uuid4().hex,
            "roles": ["verifier"],
            "group_id": "TestGroup",
        },
    )

    assert response.status_code == 200

    tenant = response.json()
    tenant_id = tenant["tenant_id"]

    response = await tenant_admin_client.get(f"{BASE_PATH}/{tenant_id}/access-token")
    assert response.status_code == 200

    token = response.json()

    assert token["access_token"]
    assert token["access_token"].startswith("tenant.ey")


@pytest.mark.anyio
async def test_create_tenant_member(
    tenant_admin_client: RichAsyncClient, tenant_admin_acapy_client: AcaPyClient
):
    name = uuid4().hex
    group_id = "TestGroup"
    response = await tenant_admin_client.post(
        BASE_PATH,
        json={"image_url": "https://image.ca", "name": name, "group_id": group_id},
    )

    assert response.status_code == 200

    tenant = response.json()

    wallet = await tenant_admin_acapy_client.multitenancy.get_wallet(
        wallet_id=tenant["tenant_id"]
    )

    assert tenant["tenant_id"] == wallet.wallet_id
    assert tenant["group_id"] == group_id
    assert tenant["tenant_name"] == name
    assert tenant["created_at"] == wallet.created_at
    assert tenant["updated_at"] == wallet.updated_at
    assert_that(wallet.settings["wallet.name"]).is_length(32)


@pytest.mark.anyio
async def test_create_tenant_issuer(
    tenant_admin_client: RichAsyncClient,
    tenant_admin_acapy_client: AcaPyClient,
    governance_acapy_client: AcaPyClient,
):
    name = uuid4().hex
    group_id = "TestGroup"
    response = await tenant_admin_client.post(
        BASE_PATH,
        json={
            "image_url": "https://image.ca",
            "name": name,
            "roles": ["issuer"],
            "group_id": group_id,
        },
    )
    assert response.status_code == 200

    tenant = response.json()
    tenant_id = tenant["tenant_id"]

    wallet = await tenant_admin_acapy_client.multitenancy.get_wallet(
        wallet_id=tenant_id
    )

    acapy_token: str = tenant["access_token"].split(".", 1)[1]
    actor = await trust_registry.actor_by_id(tenant_id)

    endorser_did = await acapy_wallet.get_public_did(governance_acapy_client)

    async with get_tenant_controller(Role.TENANT, acapy_token) as tenant_controller:
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
        assert check_webhook_state(
            client,
            "connections",
            {
                "state": "completed",
                "connection_id": connection.connection_id,
            },
        )

    # Actor
    assert_that(actor).has_name(tenant["tenant_name"])
    assert_that(actor).has_did(f"did:sov:{public_did.did}")
    assert_that(actor).has_roles(["issuer"])

    # Connection with endorser
    assert_that(connection).has_their_public_did(endorser_did.did)

    # Tenant
    assert_that(tenant).has_tenant_id(wallet.wallet_id)
    assert_that(tenant).has_tenant_name(name)
    assert_that(tenant).has_created_at(wallet.created_at)
    assert_that(tenant).has_updated_at(wallet.updated_at)
    assert_that(wallet.settings["wallet.name"]).is_length(32)


@pytest.mark.anyio
async def test_create_tenant_verifier(
    tenant_admin_client: RichAsyncClient, tenant_admin_acapy_client: AcaPyClient
):
    name = uuid4().hex
    response = await tenant_admin_client.post(
        BASE_PATH,
        json={
            "image_url": "https://image.ca",
            "name": name,
            "roles": ["verifier"],
        },
    )
    assert response.status_code == 200

    tenant = response.json()
    tenant_id = tenant["tenant_id"]

    wallet = await tenant_admin_acapy_client.multitenancy.get_wallet(
        wallet_id=tenant_id
    )

    actor = await trust_registry.actor_by_id(tenant_id)

    if not actor:
        raise Exception("Missing actor")

    acapy_token: str = tenant["access_token"].split(".", 1)[1]

    async with get_tenant_controller(Role.TENANT, acapy_token) as tenant_controller:
        connections = await tenant_controller.connection.get_connections(
            alias=f"Trust Registry {name}"
        )

    connection = connections.results[0]

    # Connection invitation
    assert_that(connection).has_state("invitation")

    assert_that(actor).has_name(tenant["tenant_name"])
    assert_that(actor).has_did(ed25519_verkey_to_did_key(connection.invitation_key))
    assert_that(actor).has_roles(["verifier"])

    # Tenant
    assert_that(tenant).has_tenant_id(wallet.wallet_id)
    assert_that(tenant).has_tenant_name(name)
    assert_that(tenant).has_created_at(wallet.created_at)
    assert_that(tenant).has_updated_at(wallet.updated_at)
    assert_that(wallet.settings["wallet.name"]).is_length(32)


@pytest.mark.anyio
async def test_update_tenant_verifier_to_issuer(
    tenant_admin_client: RichAsyncClient,
    tenant_admin_acapy_client: AcaPyClient,
    governance_acapy_client: AcaPyClient,
):
    name = uuid4().hex
    response = await tenant_admin_client.post(
        BASE_PATH,
        json={
            "image_url": "https://image.ca",
            "name": name,
            "roles": ["verifier"],
        },
    )

    tenant = response.json()
    tenant_id = tenant["tenant_id"]
    actor = await trust_registry.actor_by_id(tenant_id)

    wallet = await tenant_admin_acapy_client.multitenancy.get_wallet(
        wallet_id=tenant_id
    )
    assert_that(wallet.settings["wallet.name"]).is_length(32)

    acapy_token: str = tenant["access_token"].split(".", 1)[1]

    async with get_tenant_controller(Role.TENANT, acapy_token) as tenant_controller:
        connections = await tenant_controller.connection.get_connections(
            alias=f"Trust Registry {name}"
        )

    connection = connections.results[0]

    # Connection invitation
    assert_that(connection).has_state("invitation")

    assert actor
    assert_that(actor).has_name(name)
    assert_that(actor).has_did(ed25519_verkey_to_did_key(connection.invitation_key))
    assert_that(actor).has_roles(["verifier"])

    # Tenant
    assert_that(tenant).has_tenant_id(wallet.wallet_id)
    assert_that(tenant).has_image_url("https://image.ca")
    assert_that(tenant).has_tenant_name(name)
    assert_that(tenant).has_created_at(wallet.created_at)
    assert_that(tenant).has_updated_at(wallet.updated_at)
    assert_that(wallet.settings["wallet.name"]).is_length(32)

    new_name = uuid4().hex
    new_image_url = "https://some-ssi-site.org/image.png"
    new_roles = ["issuer", "verifier"]

    response = await tenant_admin_client.put(
        f"{BASE_PATH}/{tenant_id}",
        json={
            "image_url": new_image_url,
            "name": new_name,
            "roles": new_roles,
        },
    )
    new_tenant = response.json()
    assert_that(new_tenant).has_tenant_id(wallet.wallet_id)
    assert_that(new_tenant).has_image_url(new_image_url)
    assert_that(new_tenant).has_tenant_name(new_name)
    assert_that(new_tenant).has_created_at(wallet.created_at)

    new_actor = await trust_registry.actor_by_id(tenant_id)

    endorser_did = await acapy_wallet.get_public_did(governance_acapy_client)

    acapy_token = (
        (await tenant_admin_client.get(f"{BASE_PATH}/{tenant_id}/access-token"))
        .json()["access_token"]
        .split(".", 1)[1]
    )

    async with get_tenant_controller(Role.TENANT, acapy_token) as tenant_controller:
        public_did = await acapy_wallet.get_public_did(tenant_controller)
        assert public_did

        _connections = (await tenant_controller.connection.get_connections()).results

        connections = [
            connection
            for connection in _connections
            if connection.their_public_did == endorser_did.did
        ]

    endorser_connection = connections[0]

    async with get_tenant_client(token=tenant["access_token"]) as client:
        # Wait for connection to be completed
        assert check_webhook_state(
            client,
            "connections",
            {
                "state": "completed",
                "connection_id": endorser_connection.connection_id,
            },
        )

    # Connection invitation
    assert_that(endorser_connection).has_their_public_did(endorser_did.did)

    assert new_actor
    assert_that(new_actor).has_name(new_name)
    assert_that(new_actor).has_did(f"{new_actor['did']}")
    assert_that(new_actor["roles"]).contains_only("issuer", "verifier")

    assert new_actor["didcomm_invitation"] is not None


@pytest.mark.anyio
async def test_get_tenants(tenant_admin_client: RichAsyncClient):
    response = await tenant_admin_client.post(
        BASE_PATH,
        json={
            "image_url": "https://image.ca",
            "name": uuid4().hex,
            "roles": ["verifier"],
        },
    )

    assert response.status_code == 200
    created_tenant = response.json()
    first_tenant_id_id = created_tenant["tenant_id"]

    response = await tenant_admin_client.get(f"{BASE_PATH}/{first_tenant_id_id}")

    assert response.status_code == 200
    retrieved_tenant = response.json()
    created_tenant.pop("access_token")
    assert created_tenant == retrieved_tenant

    response = await tenant_admin_client.post(
        BASE_PATH,
        json={
            "image_url": "https://image.ca",
            "name": uuid4().hex,
            "roles": ["verifier"],
            "group_id": "ac/dc",
        },
    )

    assert response.status_code == 200
    last_tenant_id = response.json()["tenant_id"]

    response = await tenant_admin_client.get(BASE_PATH)
    assert response.status_code == 200
    tenants = response.json()
    assert len(tenants) >= 1

    # Make sure created tenant is returned
    assert_that(tenants).extracting("tenant_id").contains(last_tenant_id)
    assert_that(tenants).extracting("group_id").contains("ac/dc")


@pytest.mark.anyio
async def test_get_tenants_by_group(tenant_admin_client: RichAsyncClient):
    name = uuid4().hex
    group_id = "backstreetboys"
    response = await tenant_admin_client.post(
        BASE_PATH,
        json={
            "image_url": "https://image.ca",
            "name": name,
            "roles": ["verifier"],
            "group_id": group_id,
        },
    )

    assert response.status_code == 200
    created_tenant = response.json()
    tenant_id = created_tenant["tenant_id"]

    response = await tenant_admin_client.get(f"{BASE_PATH}?group_id={group_id}")
    assert response.status_code == 200
    tenants = response.json()
    assert len(tenants) >= 1

    # Make sure created tenant is returned
    assert_that(tenants).extracting("tenant_id").contains(tenant_id)
    assert_that(tenants).extracting("group_id").contains(group_id)

    response = await tenant_admin_client.get(f"{BASE_PATH}?group_id=spicegirls")
    assert response.status_code == 200
    tenants = response.json()
    assert len(tenants) == 0
    assert tenants == []


@pytest.mark.anyio
async def test_delete_tenant(
    tenant_admin_client: RichAsyncClient, tenant_admin_acapy_client: AcaPyClient
):
    name = uuid4().hex
    response = await tenant_admin_client.post(
        BASE_PATH,
        json={
            "image_url": "https://image.ca",
            "name": name,
            "roles": ["verifier"],
        },
    )

    assert response.status_code == 200
    tenant = response.json()
    tenant_id = tenant["tenant_id"]

    # Actor exists
    actor = await trust_registry.actor_by_id(tenant_id)
    assert actor

    response = await tenant_admin_client.delete(f"{BASE_PATH}/{tenant_id}")
    assert response.status_code == 200

    # Actor doesn't exist anymore
    actor = await trust_registry.actor_by_id(tenant_id)
    assert not actor

    with pytest.raises(Exception):
        await tenant_admin_acapy_client.multitenancy.get_wallet(wallet_id=tenant_id)
