from typing import Any, Dict, Optional, Union

from aries_cloudcontroller import IssuerCredRevRecord, IssuerRevRegRecord, OobRecord
from pydantic import BaseModel, Field

from shared.models.connection_record import Connection
from shared.models.credential_exchange import CredentialExchange
from shared.models.endorsement import Endorsement
from shared.models.presentation_exchange import PresentationExchange
from shared.models.webhook_events import WebhookEvent
from webhooks.models.topic_payloads import (
    BasicMessage,
    CredExRecordIndy,
    CredExRecordLDProof,
    DeletedCredential,
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
    group_id: Optional[str] = None
    x_wallet_id: Optional[str] = Field(None, alias="x-wallet-id")


class AcaPyRedisEvent(BaseModel):
    payload: AcaPyRedisEventPayload
    metadata: Optional[WebhookEventMetadata] = None


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
