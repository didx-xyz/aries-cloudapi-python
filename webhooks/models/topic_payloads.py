from typing import Dict, List, Literal, Optional

from aries_cloudcontroller import V20CredExRecordIndy, V20CredExRecordLDProof
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class BasicMessage(BaseModel):
    connection_id: str
    content: str
    message_id: str
    sent_time: str
    state: Optional[Literal["received"]] = None


class DescriptionInfo(TypedDict):
    en: Optional[str]
    code: Optional[str]


class ProblemReport(BaseModel):
    type: Optional[str] = Field(None, alias="@type")
    id: Optional[str] = Field(None, alias="@id")
    thread: Optional[Dict[str, str]] = Field(None, alias="~thread")
    description: Optional[DescriptionInfo] = None
    problem_items: Optional[List[Dict[str, str]]] = None
    who_retries: Optional[str] = None
    fix_hint: Optional[Dict[str, str]] = None
    impact: Optional[str] = None
    where: Optional[str] = None
    noticed_time: Optional[str] = None
    tracking_uri: Optional[str] = None
    escalation_uri: Optional[str] = None


class CredExRecordLDProof(V20CredExRecordLDProof):
    pass  # renaming ACA-Py model


class CredExRecordIndy(V20CredExRecordIndy):
    pass  # renaming ACA-Py model


class DeletedCredential(BaseModel):
    id: str
    state: Literal["deleted"]
