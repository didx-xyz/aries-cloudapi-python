import base64
import json
import time
from typing import Dict, List, Optional

import httpx
from pydantic import BaseModel

from app.tests.util.constants import WEBHOOKS_URL
from app.util.rich_async_client import RichAsyncClient
from shared_models import CloudApiTopics


class FilterMap(BaseModel):
    filter_key: str
    filter_value: str


def get_wallet_id_from_b64encoded_jwt(jwt: str) -> str:
    # Add padding if required
    # b64 needs lengths divisible by 4
    if len(jwt) % 4 != 0:
        n_missing = 4 - (len(jwt) % 4)
        jwt = jwt + (n_missing * "=")

    wallet = json.loads(base64.b64decode(jwt))
    return wallet["wallet_id"]


def get_wallet_id_from_async_client(client: RichAsyncClient) -> str:
    is_non_jwt = len(client.headers.get("x-api-key").split(".")) == 2

    if is_non_jwt:
        return "admin"

    # eg tenant_jwt: "eyJ3YWxsZXRfaWQiOiIwMzg4OTc0MC1iNDg4LTRmZjEtYWI4Ni0yOTM0NzQwZjNjNWMifQ"
    jwt = client.headers.get("x-api-key").split(".")[2]
    return get_wallet_id_from_b64encoded_jwt(jwt)


def check_webhook_state(
    client: RichAsyncClient,
    topic: CloudApiTopics,
    filter_map: Dict[str, Optional[str]],
    max_duration: int = 120,
    poll_interval: int = 1,
) -> bool:
    assert poll_interval >= 0, "Poll interval cannot be negative"
    assert max_duration >= 0, "Poll duration cannot be negative"

    wallet_id = get_wallet_id_from_async_client(client)

    t_end = time.time() + max_duration
    while time.time() < t_end:
        hooks_response = httpx.get(f"{WEBHOOKS_URL}/webhooks/{topic}/{wallet_id}")

        if hooks_response.is_error:
            raise Exception(
                f"Error retrieving webhooks: {hooks_response.text}")

        hooks = hooks_response.json()

        # Loop through all hooks
        for hook in hooks:
            payload = hook["payload"]
            # Find the right hook
            match = all(
                payload.get(filter_key, None) == filter_value
                for filter_key, filter_value in filter_map.items()
            )

            if match:
                return True

        time.sleep(poll_interval)
    raise Exception(
        f"Cannot satisfy webhook filter \n{filter_map}\n. Found \n{hooks}")


def get_hooks_per_topic_per_wallet(client: RichAsyncClient, topic: CloudApiTopics) -> List:
    wallet_id = get_wallet_id_from_async_client(client)
    try:
        hooks = (httpx.get(f"{WEBHOOKS_URL}/webhooks/{topic}/{wallet_id}")).json()
        return hooks if hooks else []
    except httpx.HTTPError as e:
        raise e from e
