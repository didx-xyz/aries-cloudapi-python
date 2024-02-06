from enum import Enum
from typing import Dict, List, Optional

from aries_cloudcontroller import LDProofVCDetail
from pydantic import BaseModel, Field, ValidationInfo, field_validator

from shared.models.protocol import IssueCredentialProtocolVersion


class CredentialType(str, Enum):
    INDY: str = "indy"
    JWT: str = "jwt"
    LD_PROOF: str = "ld_proof"


class IndyCredential(BaseModel):
    credential_definition_id: str
    attributes: Dict[str, str]


class CredentialBase(BaseModel):
    type: CredentialType = CredentialType.INDY
    indy_credential_detail: Optional[IndyCredential] = None
    ld_credential_detail: Optional[LDProofVCDetail] = None
    save_exchange_record: bool = Field(
        default=False,
        description="Whether the credential exchange record should be saved on completion",
    )

    @field_validator("indy_credential_detail", mode="before")
    @classmethod
    def check_indy_credential_detail(cls, value, values: ValidationInfo):
        if values.data.get("type") == CredentialType.INDY and value is None:
            raise ValueError(
                "indy_credential_detail must be populated if `indy` credential type is selected"
            )
        return value

    @field_validator("ld_credential_detail", mode="before")
    @classmethod
    def check_ld_credential_detail(cls, value, values: ValidationInfo):
        if values.data.get("type") == CredentialType.LD_PROOF and value is None:
            raise ValueError(
                "ld_credential_detail must be populated if `ld_proof` credential type is selected"
            )
        return value


class CredentialWithConnection(CredentialBase):
    connection_id: str


class CredentialWithProtocol(CredentialBase):
    protocol_version: IssueCredentialProtocolVersion = IssueCredentialProtocolVersion.v2


class SendCredential(CredentialWithProtocol, CredentialWithConnection):
    pass


class CreateOffer(CredentialWithProtocol):
    pass


class RevokeCredential(BaseModel):
    credential_exchange_id: str
    credential_definition_id: Optional[str] = None
    auto_publish_on_ledger: Optional[bool] = False


class PublishRevocationsRequest(BaseModel):
    revocation_registry_credential_map: Dict[str, List[str]] = Field(
        default={},
        description=(
            "A map of revocation registry IDs to lists of credential revocation IDs that should be published."
            "Providing an empty list for a registry ID publishes all pending revocations for that ID. "
            "An empty dictionary signifies that the action should be applied to all pending revocations across "
            "all registry IDs."
        ),
    )


class ClearPendingRevocationsRequest(BaseModel):
    revocation_registry_credential_map: Dict[str, List[str]] = Field(
        default={},
        description=(
            "A map of revocation registry IDs to lists of credential revocation IDs for which pending revocations"
            "should be cleared. Providing an empty list for a registry ID clears all pending revocations for that ID. "
            "An empty dictionary signifies that the action should be applied to clear all pending revocations across "
            "all registry IDs."
        ),
    )


class ClearPendingRevocationsResult(BaseModel):
    revocation_registry_credential_map: Dict[str, List[str]] = Field(
        description=(
            "The resulting revocations that are still pending after a clear-pending request has been completed."
        ),
    )
