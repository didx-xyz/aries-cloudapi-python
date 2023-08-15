from enum import Enum
from typing import Optional

from aries_cloudcontroller import (
    DIFPresSpec,
    DIFProofRequest,
    IndyPresSpec,
    IndyProofRequest,
)
from pydantic import BaseModel, validator

from shared.models.protocol import PresentProofProtocolVersion


class ProofRequestType(Enum):
    INDY = "indy"
    JWT = "jwt"
    LD_PROOF = "ld_proof"


class ProofRequestBase(BaseModel):
    type: ProofRequestType = ProofRequestType.INDY
    indy_proof_request: Optional[IndyProofRequest]
    dif_proof_request: Optional[DIFProofRequest]

    @validator("indy_proof_request", pre=True, always=True)
    @classmethod
    def check_indy_proof_request(cls, value, values):
        if values.get("type") == ProofRequestType.INDY and value is None:
            raise ValueError(
                "indy_proof_request must be populated if `indy` type is selected"
            )
        return value

    @validator("dif_proof_request", pre=True, always=True)
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
    indy_presentation_spec: Optional[IndyPresSpec]
    dif_presentation_spec: Optional[DIFPresSpec]

    @validator("indy_presentation_spec", pre=True, always=True)
    @classmethod
    def check_indy_presentation_spec(cls, value, values):
        if values.get("type") == ProofRequestType.INDY and value is None:
            raise ValueError(
                "indy_presentation_spec must be populated if `indy` type is selected"
            )
        return value

    @validator("dif_presentation_spec", pre=True, always=True)
    @classmethod
    def check_dif_presentation_spec(cls, value, values):
        if values.get("type") == ProofRequestType.LD_PROOF and value is None:
            raise ValueError(
                "dif_presentation_spec must be populated if `ld_proof` type is selected"
            )
        return value


class RejectProofRequest(ProofId):
    problem_report: Optional[str] = None
