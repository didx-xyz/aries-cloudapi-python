from enum import Enum
from typing import Optional

from aries_cloudcontroller import (
    DIFPresSpec,
    DIFProofRequest,
    IndyPresSpec,
    IndyProofRequest,
)
from pydantic import BaseModel, field_validator

from shared.models.protocol import PresentProofProtocolVersion


class ProofRequestType(str, Enum):
    INDY: str = "indy"
    JWT: str = "jwt"
    LD_PROOF: str = "ld_proof"


class ProofRequestBase(BaseModel):
    type: ProofRequestType = ProofRequestType.INDY
    indy_proof_request: Optional[IndyProofRequest] = None
    dif_proof_request: Optional[DIFProofRequest] = None

    @field_validator("indy_proof_request", mode="before", always=True)
    @classmethod
    def check_indy_proof_request(cls, value, values):
        if values.get("type") == ProofRequestType.INDY and value is None:
            raise ValueError(
                "indy_proof_request must be populated if `indy` type is selected"
            )
        return value

    @field_validator("dif_proof_request", mode="before", always=True)
    @classmethod
    def check_dif_proof_request(cls, value, values):
        if values.get("type") == ProofRequestType.LD_PROOF and value is None:
            raise ValueError(
                "dif_proof_request must be populated if `ld_proof` type is selected"
            )
        return value


class ProofRequestMetadata(BaseModel):
    protocol_version: PresentProofProtocolVersion = PresentProofProtocolVersion.v2
    auto_verify: Optional[bool] = None
    comment: Optional[str] = None
    trace: Optional[bool] = None


class CreateProofRequest(ProofRequestBase, ProofRequestMetadata):
    pass


class SendProofRequest(CreateProofRequest):
    connection_id: str


class ProofId(BaseModel):
    proof_id: str


class AcceptProofRequest(ProofId):
    type: ProofRequestType = ProofRequestType.INDY
    indy_presentation_spec: Optional[IndyPresSpec] = None
    dif_presentation_spec: Optional[DIFPresSpec] = None

    @field_validator("indy_presentation_spec", mode="before", always=True)
    @classmethod
    def check_indy_presentation_spec(cls, value, values):
        if values.get("type") == ProofRequestType.INDY and value is None:
            raise ValueError(
                "indy_presentation_spec must be populated if `indy` type is selected"
            )
        return value

    @field_validator("dif_presentation_spec", mode="before", always=True)
    @classmethod
    def check_dif_presentation_spec(cls, value, values):
        if values.get("type") == ProofRequestType.LD_PROOF and value is None:
            raise ValueError(
                "dif_presentation_spec must be populated if `ld_proof` type is selected"
            )
        return value


class RejectProofRequest(ProofId):
    problem_report: Optional[str] = None
