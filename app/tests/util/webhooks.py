from typing import Dict, Optional

from app.event_handling.sse_listener import SseListener
from app.util.tenants import get_wallet_id_from_b64encoded_jwt
from shared import RichAsyncClient
from shared.models.webhook_topics import CloudApiTopics


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
    max_duration: int = 30,
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
        raise Exception(f"Could not satisfy webhook filter: `{filter_map}`.")
