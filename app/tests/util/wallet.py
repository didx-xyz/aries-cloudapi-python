from httpx import AsyncClient


async def create_and_set_public_did(member_client: AsyncClient):
    pub_did_res = await member_client.get("/wallet/create-pub-did")

    if pub_did_res.status_code != 200:
        raise Exception(f"Error registering public did: {pub_did_res.text}")

    return pub_did_res.json()
