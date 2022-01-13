import time
import os

from httpx import AsyncClient
import httpx

from app.tests.util.string import get_wallet_id_from_JWT

PORT = os.getenv("PORT", "3010")
URL = os.getenv("BROADCAST_URL", "yoma-webhooks-web")


def check_webhook_state(
    client: AsyncClient,
    desired_state: dict,
    max_duration: int = 10,
    poll_intervall: int = 1,
):
    assert (poll_intervall >= 0, "Poll interval cannot be negative")
    assert (max_duration >= 0, "Poll duration cannot be negative")

    wallet_id = get_wallet_id_from_JWT(client)

    t_end = time.time() + max_duration
    while time.time() < t_end:
        conns = (httpx.get(f"http://localhost:3010/connections/{wallet_id}")).json()
        states = [d["payload"][list(desired_state.keys())[0]] for d in conns]
        time.sleep(poll_intervall)
        if list(desired_state.values())[0] in states:
            return True
    raise Exception(f"Cannot satify {desired_state}. \nFound {states}")
