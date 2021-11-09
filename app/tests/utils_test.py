import random
import string
from httpx import AsyncClient

APPLICATION_JSON_CONTENT_TYPE = {"content-type": "application/json"}
CONNECTIONS_BASE_PATH = "/generic/connections"
WALLET_MULTITENANT_BASE_PATH = "/admin/wallet-multitenant"

def get_random_string(length: int):
    letters = string.ascii_uppercase
    return "".join(random.choice(letters) for _ in range(length))

async def remove_wallet(async_client: AsyncClient, wallet_id: str, role: str = "member"):
     return await async_client.delete(
        f"{WALLET_MULTITENANT_BASE_PATH}/{wallet_id}",
        headers={"x-api-key": "adminApiKey", "x-role": role},
    )

async def create_wallet(async_client: AsyncClient, wallet_name: str, role: str = "member"):
     rand = random.random()

     return await async_client.post(
       f"{WALLET_MULTITENANT_BASE_PATH}/create-wallet",
        headers={
            "x-api-key": "adminApiKey",
            "x-role": role,
            **APPLICATION_JSON_CONTENT_TYPE,
        },
        json={
            "image_url": "https://aries.ca/images/sample.png",
            "key_management_mode": "managed",
            "label": "YOMA",
            "wallet_dispatch_type": "default",
            "wallet_key": "MySecretKey1234",
            "wallet_name": wallet_name + "-" + str(rand),
            "wallet_type": "indy",
        }
    )

async def get_wallet_token(async_client: AsyncClient, wallet_id: str, role: str = "member"):
    token_response = await async_client.get(
        f"{WALLET_MULTITENANT_BASE_PATH}/{wallet_id}/auth-token",
        headers={
            "x-api-key": "adminApiKey",
            "x-role": role,
            **APPLICATION_JSON_CONTENT_TYPE,
        },
    )

    return token_response.json()["token"]

async def create_invitation(async_client: AsyncClient, token: str, role: str = "member"):

    invitation_creation_response = await async_client.post(
        f"{CONNECTIONS_BASE_PATH}/create-invitation",
        headers={
            "x-auth": f"Bearer {token}",
            "x-role": role,
            **APPLICATION_JSON_CONTENT_TYPE,
        },
    )

    return invitation_creation_response.json()["invitation"]
