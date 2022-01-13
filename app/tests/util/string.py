import random
import string
import json
import base64

from httpx import AsyncClient


def get_random_string(length: int):
    letters = string.ascii_uppercase
    return "".join(random.choice(letters) for _ in range(length))


def get_wallet_id_from_JWT(client: AsyncClient) -> str:

    api_key = client.headers["x-api-key"]
    payload = api_key.split(".")
    wallet_64 = payload[2]
    if len(wallet_64) % 4 != 0:
        n_missing = len(wallet_64) % 4
        wallet_64 = wallet_64 + n_missing * "="

    wallet = json.loads(base64.b64decode(wallet_64))
    return wallet["wallet_id"]
