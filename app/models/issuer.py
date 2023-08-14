from enum import Enum
from typing import Dict, Optional

from aries_cloudcontroller import LDProofVCDetail
from pydantic import BaseModel, validator

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

    @validator("indy_credential_detail", pre=True, always=True)
    def check_indy_credential_detail(self, value, values):
        if values.get("type") == CredentialType.INDY and value is None:
            raise ValueError(
                "indy_credential_detail must be populated if CredentialType.INDY is selected"
            )
        return value

    @validator("ld_credential_detail", pre=True, always=True)
    def check_ld_credential_detail(self, value, values):
        if values.get("type") == CredentialType.LD_PROOF and value is None:
            raise ValueError(
                "ld_credential_detail must be populated if CredentialType.LD_PROOF is selected"
            )
        return value


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
