import asyncio
from uuid import uuid4
from aries_cloudcontroller.acapy_client import AcaPyClient
from assertpy.assertpy import assert_that
import pytest

from httpx import AsyncClient
from app.dependencies import get_tenant_controller
from app.facades import acapy_wallet, trust_registry
from app.role import Role

# Tests are broken if we import the event_loop...
@pytest.yield_fixture(scope="session")
def event_loop(request):
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


from app.tests.util.webhooks import (
    check_webhook_state,
)

from app.tests.util.client import tenant_client

from app.admin.tenants import tenants
from app.util.did import ed25519_verkey_to_did_key

BASE_PATH = tenants.router.prefix


@pytest.mark.asyncio
async def test_get_tenant_auth_token(tenant_admin_client: AsyncClient):
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

    response = await tenant_admin_client.get(f"{BASE_PATH}/{tenant_id}/access-token")
    assert response.status_code == 200

    token = response.json()

    assert token["access_token"]
    assert token["access_token"].startswith("tenant.ey")


@pytest.mark.asyncio
async def test_create_tenant_member(
    tenant_admin_client: AsyncClient, tenant_admin_acapy_client: AcaPyClient
):
    name = uuid4().hex
    response = await tenant_admin_client.post(
        BASE_PATH,
        json={"image_url": "https://image.ca", "name": name},
    )

    assert response.status_code == 200

    tenant = response.json()

    wallet = await tenant_admin_acapy_client.multitenancy.get_wallet(
        wallet_id=tenant["tenant_id"]
    )

    assert tenant["tenant_id"] == wallet.wallet_id
    assert tenant["tenant_name"] == name
    assert tenant["created_at"] == wallet.created_at
    assert tenant["updated_at"] == wallet.updated_at
    assert_that(wallet.settings["wallet.name"]).is_length(32)


@pytest.mark.asyncio
async def test_create_tenant_issuer(
    tenant_admin_client: AsyncClient,
    tenant_admin_acapy_client: AcaPyClient,
    governance_acapy_client: AcaPyClient,
):
    name = uuid4().hex
    response = await tenant_admin_client.post(
        BASE_PATH,
        json={
            "image_url": "https://image.ca",
            "name": name,
            "roles": ["issuer"],
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

    async with tenant_client(token=tenant["access_token"]) as client:
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


@pytest.mark.asyncio
async def test_create_tenant_verifier(
    tenant_admin_client: AsyncClient, tenant_admin_acapy_client: AcaPyClient
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


@pytest.mark.asyncio
async def test_update_tenant_verifier_to_issuer(
    tenant_admin_client: AsyncClient,
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
    assert response.status_code == 200

    tenant = response.json()
    tenant_id = tenant["tenant_id"]
    actor = await trust_registry.actor_by_id(tenant_id)

    wallet = await tenant_admin_acapy_client.multitenancy.get_wallet(
        wallet_id=tenant_id
    )

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

    assert response.status_code == 200
    new_tenant = response.json()
    new_actor = await trust_registry.actor_by_id(tenant_id)

    endorser_did = await acapy_wallet.get_public_did(governance_acapy_client)

    async with get_tenant_controller(Role.TENANT, acapy_token) as tenant_controller:
        public_did = await acapy_wallet.get_public_did(tenant_controller)

        _connections = (await tenant_controller.connection.get_connections()).results

        connections = [
            connection
            for connection in _connections
            if connection.their_public_did == endorser_did.did
        ]

    endorser_connection = connections[0]

    async with tenant_client(token=tenant["access_token"]) as client:
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
    assert_that(new_actor).has_did(f"did:sov:{public_did.did}")
    assert_that(new_actor["roles"]).contains_only("issuer", "verifier")

    assert new_actor["didcomm_invitation"] is None

    # Tenant
    assert_that(new_tenant).has_tenant_id(wallet.wallet_id)
    assert_that(new_tenant).has_image_url(new_image_url)
    assert_that(new_tenant).has_tenant_name(new_name)
    assert_that(new_tenant).has_created_at(wallet.created_at)
    assert_that(wallet.settings["wallet.name"]).is_length(32)


@pytest.mark.asyncio
async def test_get_tenant(tenant_admin_client: AsyncClient):
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
    created_tenant = response.json()
    tenant_id = created_tenant["tenant_id"]

    response = await tenant_admin_client.get(f"{BASE_PATH}/{tenant_id}")

    assert response.status_code == 200
    retrieved_tenant = response.json()
    created_tenant.pop("access_token")
    assert created_tenant == retrieved_tenant


@pytest.mark.asyncio
async def test_get_tenants(tenant_admin_client: AsyncClient):
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
    created_tenant = response.json()
    tenant_id = created_tenant["tenant_id"]

    response = await tenant_admin_client.get(BASE_PATH)
    assert response.status_code == 200
    tenants = response.json()
    assert len(tenants) >= 1

    # Make sure created tenant is returned
    assert_that(tenants).extracting("tenant_id").contains(tenant_id)


@pytest.mark.asyncio
async def test_delete_tenant(
    tenant_admin_client: AsyncClient, tenant_admin_acapy_client: AcaPyClient
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
