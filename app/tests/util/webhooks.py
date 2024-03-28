from typing import Dict, Optional

from app.services.event_handling.sse_listener import SseListener
from app.util.tenants import get_wallet_id_from_b64encoded_jwt
from shared import RichAsyncClient
from shared.models.webhook_events import CloudApiTopics


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
    state: str,
    filter_map: Optional[Dict[str, str]] = None,
    max_duration: int = 60,
    lookback_time: int = 1,
) -> bool:
    assert max_duration >= 0, "Poll duration cannot be negative"

    wallet_id = get_wallet_id_from_async_client(client)

    listener = SseListener(wallet_id, topic)

    # Check if there are any other keys
    if filter_map:
        # Assuming that filter_map contains max 1 other key-value pair
        field, field_id = list(filter_map.items())[0]

        event = await listener.wait_for_event(
            field=field,
            field_id=field_id,
            desired_state=state,
            timeout=max_duration,
            lookback_time=lookback_time,
        )
    else:
        # No other key means we are only asserting the state
        event = await listener.wait_for_state(
            desired_state=state,
            timeout=max_duration,
            lookback_time=lookback_time,
        )

    if event:
        return event
    else:
        raise Exception(f"Could not satisfy webhook filter: `{filter_map}`.")
