import base64
import json
from typing import Dict, List, Optional

import httpx
from pydantic import BaseModel

from app.event_handling.sse_listener import SseListener
from shared import WEBHOOKS_URL, CloudApiTopics, RichAsyncClient


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


async def check_webhook_state(
    client: RichAsyncClient,
    topic: CloudApiTopics,
    filter_map: Dict[str, Optional[str]],
    max_duration: int = 120,
) -> bool:
    assert max_duration >= 0, "Poll duration cannot be negative"

    wallet_id = get_wallet_id_from_async_client(client)

    listener = SseListener(wallet_id, topic)

    desired_state = filter_map["state"]

    other_keys = dict(filter_map)
    other_keys.pop("state", None)

    # Check if there are any other keys
    if other_keys:
        # Assuming that filter_map contains max 1 other key-value pair
        field, field_id = list(other_keys.items())[0]

        event = await listener.wait_for_event(
            field=field,
            field_id=field_id,
            desired_state=desired_state,
            timeout=max_duration,
        )
    else:
        # No other key means we are only asserting the state
        event = await listener.wait_for_state(
            desired_state=desired_state, timeout=max_duration
        )

    if event:
        return True
    else:
        raise Exception(f"Could not satisfy webhook filter: {filter_map}.")


def get_hooks_per_topic_per_wallet(
    client: RichAsyncClient, topic: CloudApiTopics
) -> List:
    wallet_id = get_wallet_id_from_async_client(client)
    try:
        with httpx.Client() as client:
            hooks = client.get(f"{WEBHOOKS_URL}/webhooks/{wallet_id}/{topic}").json()
        return hooks if hooks else []
    except httpx.HTTPError as e:
        raise e from e
