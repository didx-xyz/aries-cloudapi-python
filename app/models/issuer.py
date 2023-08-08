from typing import Dict, Optional

from aries_cloudcontroller import Credential as AcaCredential
from aries_cloudcontroller import LDProofVCDetailOptions
from pydantic import BaseModel

from shared.models.protocol import IssueCredentialProtocolVersion


class Credential(BaseModel):
    connection_id: str
    cred_def_id: str
    attributes: Dict[str, str]


class JsonLdCredential(BaseModel):
    connection_id: str
    credential: AcaCredential
    options: LDProofVCDetailOptions


class CredentialNoConnection(BaseModel):
    cred_def_id: str
    attributes: Dict[str, str]


class CredentialBase(BaseModel):
    protocol_version: IssueCredentialProtocolVersion
    credential_definition_id: str
    attributes: Dict[str, str]


class RevokeCredential(BaseModel):
    credential_exchange_id: str
    credential_definition_id: str = ""
    auto_publish_on_ledger: Optional[bool] = False


class SendCredential(CredentialBase):
    connection_id: str


class CreateOffer(CredentialBase):
    pass
