from enum import Enum
from typing import Optional

from aries_cloudcontroller import DIFProofRequest, IndyPresSpec, IndyProofRequest
from pydantic import BaseModel

from shared.models.protocol import PresentProofProtocolVersion


class ProofRequestType(Enum):
    INDY = "indy"
    JWT = "jwt"
    LD_PROOF = "ld_proof"


class ProofRequestBase(BaseModel):
    type: ProofRequestType = ProofRequestType.INDY
    indy_proof_request: Optional[IndyProofRequest]
    ld_proof_request: Optional[DIFProofRequest]


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
