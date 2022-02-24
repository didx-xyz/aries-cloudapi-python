import time
from typing import List

from httpx import AsyncClient
import httpx
from pydantic import BaseModel

from app.facades.webhooks import topics
from app.facades.webhooks import get_wallet_id_from_client
from app.tests.util.constants import WEBHOOKS_URL


class FilterMap(BaseModel):
    filter_key: str
    filter_value: str


def check_webhook_state(
    client: AsyncClient,
    topic: topics,
    filter_map: dict = None,
    max_duration: int = 15,
    poll_interval: int = 1,
) -> bool:
    assert poll_interval >= 0, "Poll interval cannot be negative"
    assert max_duration >= 0, "Poll duration cannot be negative"

    wallet_id = get_wallet_id_from_client(client)

    t_end = time.time() + max_duration
    while time.time() < t_end:
        hooks = (httpx.get(f"{WEBHOOKS_URL}/{topic}/{wallet_id}")).json()
        if filter_map:
            for filter_key, filter_value in filter_map.items():
                hooks = [
                    h
                    for h in hooks
                    # strip the protocol identifier that was added 0016- and 0023-
                    if (h["payload"][filter_key])
                    .replace("0016-", "")
                    .replace("0023-", "")
                    == filter_value
                ]
            states = [d["payload"]["state"] for d in hooks]
            time.sleep(poll_interval)
            if filter_map["state"] in states:
                return True
    raise Exception(f"Cannot satify state {filter_map['state']}. \nFound {states}")


def get_hooks_per_topic_per_wallet(client: AsyncClient, topic: topics) -> List:
    wallet_id = get_wallet_id_from_client(client)
    try:
        hooks = (httpx.get(f"{WEBHOOKS_URL}/{topic}/{wallet_id}")).json()
        return hooks if hooks else []
    except httpx.HTTPError as e:
        raise e from e
