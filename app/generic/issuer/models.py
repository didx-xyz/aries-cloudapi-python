from typing import Dict, Optional

from pydantic import BaseModel
from typing_extensions import TypedDict

from shared import IssueCredentialProtocolVersion


class Credential(BaseModel):
    connection_id: str
    cred_def_id: str
    attributes: Dict[str, str]


class CredentialNoConnection(BaseModel):
    cred_def_id: str
    attributes: Dict[str, str]


class ProblemReportExplanation(TypedDict):
    description: str


class CredentialBase(BaseModel):
    protocol_version: IssueCredentialProtocolVersion
    credential_definition_id: str
    attributes: Dict[str, str]


class RevokeCredential(BaseModel):
    credential_definition_id: str = ""
    auto_publish_on_ledger: Optional[bool] = False
    credential_exchange_id: str = ""


class SendCredential(CredentialBase):
    connection_id: str


class CreateOffer(CredentialBase):
    pass
