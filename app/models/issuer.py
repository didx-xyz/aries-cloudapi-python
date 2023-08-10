from enum import Enum
from typing import Dict, Optional

from aries_cloudcontroller import Credential as AcaCredential
from aries_cloudcontroller import LDProofVCDetailOptions
from pydantic import BaseModel

from shared.models.protocol import IssueCredentialProtocolVersion


class CredentialType(Enum):
    INDY = "indy"
    JWT = "jwt"
    LD_PROOF = "ld_proof"


class IndyCredential(BaseModel):
    credential_definition_id: str
    attributes: Dict[str, str]


class CredentialBase(BaseModel):
    type: CredentialType = CredentialType.INDY
    indy_credential_detail: Optional[IndyCredential]
    ld_credential_detail: Optional[LDProofVCDetail]


class CredentialWithConnection(CredentialBase):
    connection_id: str


class CredentialWithProtocol(CredentialBase):
    protocol_version: IssueCredentialProtocolVersion


class SendCredential(CredentialWithProtocol, CredentialWithConnection):
    pass


class CreateOffer(CredentialWithProtocol):
    pass


class RevokeCredential(BaseModel):
    credential_exchange_id: str
    credential_definition_id: Optional[str] = None
    auto_publish_on_ledger: Optional[bool] = False


class JsonLdCredential(BaseModel):
    connection_id: str
    credential: AcaCredential
    options: LDProofVCDetailOptions
