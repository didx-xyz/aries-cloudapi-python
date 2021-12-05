from httpx import AsyncClient

from .string import get_random_string


async def create_member_wallet(member_admin_client: AsyncClient, name: str):
    full_name = f"{name}{get_random_string(3)}"
    wallet_payload = {
        "image_url": "https://aries.ca/images/sample.png",
        "label": full_name,
        "wallet_key": "MySecretKey1234",
        "wallet_type": "indy",
        "wallet_name": full_name,
    }

    wallet_response = await member_admin_client.post(
        "/admin/wallet-multitenant/create-wallet", json=wallet_payload
    )
    wallet = wallet_response.json()

    return wallet


async def delete_member_wallet(member_admin_client: AsyncClient, wallet_id: str):
    await member_admin_client.delete(f"/admin/wallet-multitenant/{wallet_id}")
