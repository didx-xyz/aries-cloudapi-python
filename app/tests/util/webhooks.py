import time
import os
from typing import List, Literal

from httpx import AsyncClient
import httpx

from app.tests.util.string import get_wallet_id_from_JWT

WEBHOOKS_URL = os.getenv("WEBHOOKS_URL", "http://localhost:3010")

topics = Literal[
    "connections",
    "issue_credential",
    "forward",
    "ping",
    "basicmessages",
    "issuer_cred_rev",
    "issue_credential_v2_0",
    "issue_credential_v2_0_indy",
    "issue_credential_v2_0_dif",
    "present_proof",
    "revocation_registry",
]


def check_webhook_state(
    client: AsyncClient,
    desired_state: dict = None,
    topic: topics = "connections",
    max_duration: int = 10,
    poll_intervall: int = 1,
) -> bool:
    assert (poll_intervall >= 0, "Poll interval cannot be negative")
    assert (max_duration >= 0, "Poll duration cannot be negative")

    wallet_id = get_wallet_id_from_JWT(client)

    t_end = time.time() + max_duration
    while time.time() < t_end:
        hooks = (httpx.get(f"{WEBHOOKS_URL}/{topic}/{wallet_id}")).json()
        states = [d["payload"][list(desired_state.keys())[0]] for d in hooks]
        time.sleep(poll_intervall)
        if list(desired_state.values())[0] in states:
            return True
    raise Exception(f"Cannot satify {desired_state}. \nFound {states}")


def get_hooks_per_topic_per_wallet(client: AsyncClient, topic: topics) -> List:
    wallet_id = get_wallet_id_from_JWT(client)
    try:
        hooks = (httpx.get(f"{WEBHOOKS_URL}/{topic}/{wallet_id}")).json()
        return hooks if hooks else []
    except httpx.HTTPError as e:
        raise e from e
