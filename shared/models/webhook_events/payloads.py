from typing import Any, Dict, Optional

from pydantic import BaseModel


class WebhookEvent(BaseModel):
    wallet_id: str
    topic: str
    origin: str
    group_id: Optional[str] = None


# When reading json webhook events from redis and deserializing back into a CloudApiWebhookEvent,
# it does not always parse to the correct WebhookEventPayloadType for the payload.
# So, use the generic version when parsing redis events
class CloudApiWebhookEventGeneric(WebhookEvent):
    payload: Dict[str, Any]
