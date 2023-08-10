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


class CredentialWithConnection(CredentialNoConnection):
    connection_id: str


class CredentialWithProtocol(CredentialNoConnection):
    protocol_version: IssueCredentialProtocolVersion


class SendCredential(CredentialWithConnection):
    pass


class CreateOffer(CredentialWithProtocol):
    pass


class RevokeCredential(BaseModel):
    credential_exchange_id: str
    credential_definition_id: str = ""
    auto_publish_on_ledger: Optional[bool] = False


class JsonLdCredential(BaseModel):
    connection_id: str
    credential: AcaCredential
    options: LDProofVCDetailOptions
