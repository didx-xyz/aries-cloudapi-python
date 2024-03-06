from typing import Any, Dict, Optional, Union

from aries_cloudcontroller import IssuerCredRevRecord, IssuerRevRegRecord, OobRecord
from pydantic import BaseModel, Field

from shared.models.webhook_topics import (
    BasicMessage,
    Connection,
    CredentialExchange,
    CredExRecordIndy,
    CredExRecordLDProof,
    DeletedCredential,
    Endorsement,
    PresentationExchange,
    ProblemReport,
)


class AcaPyRedisEventPayload(BaseModel):
    wallet_id: str
    state: Optional[str] = None
    topic: str
    category: Optional[str] = None
    payload: Dict[str, Any]


class WebhookEventMetadata(BaseModel):
    time_ns: int
    origin: Optional[str] = None
    x_wallet_id: Optional[str] = Field(None, alias="x-wallet-id")


class AcaPyRedisEvent(BaseModel):
    payload: AcaPyRedisEventPayload
    metadata: Optional[WebhookEventMetadata] = None


class WebhookEvent(BaseModel):
    wallet_id: str
    topic: str
    origin: str


class AcaPyWebhookEvent(WebhookEvent):
    acapy_topic: str
    payload: Dict[str, Any]


WebhookEventPayloadType = Union[
    BasicMessage,
    Connection,
    CredentialExchange,
    CredExRecordIndy,
    CredExRecordLDProof,
    DeletedCredential,
    Endorsement,
    IssuerCredRevRecord,
    IssuerRevRegRecord,
    OobRecord,
    PresentationExchange,
    ProblemReport,
]


class CloudApiWebhookEvent(WebhookEvent):
    payload: WebhookEventPayloadType


# When reading json webhook events from redis and deserialising back into a CloudApiWebhookEvent,
# it does not always parse to the correct WebhookEventPayloadType for the payload.
# So, use the generic version when parsing redis events
class CloudApiWebhookEventGeneric(WebhookEvent):
    payload: Dict[str, Any]
