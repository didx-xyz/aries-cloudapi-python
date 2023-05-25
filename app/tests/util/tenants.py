from httpx import AsyncClient

from app.tests.util.string import get_random_string


async def create_issuer_tenant(tenant_admin_client: AsyncClient, name: str):
    full_name = f"{name}{get_random_string(3)}"
    wallet_payload = {"name": full_name, "roles": ["issuer"], "group_id": "IssuerGroup"}

    wallet_response = await tenant_admin_client.post(
        "/admin/tenants", json=wallet_payload
    )

    if wallet_response.is_error:
        raise Exception(f"Could not create issuer tenant. {wallet_response.text}")

    wallet = wallet_response.json()

    return wallet


async def create_verifier_tenant(tenant_admin_client: AsyncClient, name: str):
    full_name = f"{name}{get_random_string(3)}"
    wallet_payload = {
        "name": full_name,
        "roles": ["verifier"],
        "group_id": "VerifierGroup",
    }

    wallet_response = await tenant_admin_client.post(
        "/admin/tenants", json=wallet_payload
    )

    if wallet_response.is_error:
        raise Exception(f"Could not create verifier tenant. {wallet_response.text}")

    wallet = wallet_response.json()

    return wallet


async def create_tenant(tenant_admin_client: AsyncClient, name: str):
    full_name = f"{name}{get_random_string(3)}"
    wallet_payload = {
        "image_url": "https://aries.ca/images/sample.png",
        "name": full_name,
        "group_id": "TenantGroup",
    }

    wallet_response = await tenant_admin_client.post(
        "/admin/tenants", json=wallet_payload
    )
    wallet = wallet_response.json()

    return wallet


async def delete_tenant(admin_client: AsyncClient, tenant_id: str):
    await admin_client.delete(f"/admin/tenants/{tenant_id}")
