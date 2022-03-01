from httpx import AsyncClient

from .string import get_random_string


async def create_tenant(member_admin_client: AsyncClient, name: str):
    full_name = f"{name}{get_random_string(3)}"
    wallet_payload = {
        "image_url": "https://aries.ca/images/sample.png",
        "name": full_name,
    }

    wallet_response = await member_admin_client.post(
        "/admin/tenants", json=wallet_payload
    )
    wallet = wallet_response.json()

    return wallet


async def delete_tenant(member_admin_client: AsyncClient, tenant_id: str):
    await member_admin_client.delete(f"/admin/tenants/{tenant_id}")
