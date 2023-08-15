from enum import Enum
from typing import Optional

from aries_cloudcontroller import DIFProofRequest, IndyPresSpec, IndyProofRequest
from pydantic import BaseModel, validator

from shared.models.protocol import PresentProofProtocolVersion


class ProofRequestType(Enum):
    INDY = "indy"
    JWT = "jwt"
    LD_PROOF = "ld_proof"


class ProofRequestBase(BaseModel):
    type: ProofRequestType = ProofRequestType.INDY
    indy_proof_request: Optional[IndyProofRequest]
    ld_proof_request: Optional[DIFProofRequest]

    @validator("indy_proof_request", pre=True, always=True)
    @classmethod
    def check_indy_proof_request(cls, value, values):
        if values.get("type") == ProofRequestType.INDY and value is None:
            raise ValueError(
                "indy_proof_request must be populated if ProofRequestType.INDY is selected"
            )
        return value

    @validator("ld_proof_request", pre=True, always=True)
    @classmethod
    def check_ld_proof_request(cls, value, values):
        if values.get("type") == ProofRequestType.LD_PROOF and value is None:
            raise ValueError(
                "ld_proof_request must be populated if ProofRequestType.LD_PROOF is selected"
            )
        return value


class ProofRequestMetadata(BaseModel):
    protocol_version: PresentProofProtocolVersion
    auto_verify: Optional[bool] = None
    comment: Optional[str] = None
    trace: Optional[bool] = None


class CreateProofRequest(ProofRequestBase, ProofRequestMetadata):
    pass


class SendProofRequest(CreateProofRequest):
    connection_id: str


class ProofId(BaseModel):
    proof_id: str


class AcceptProofRequest(ProofRequestBase, ProofId):
    pass


class RejectProofRequest(ProofId):
    problem_report: Optional[str] = None
