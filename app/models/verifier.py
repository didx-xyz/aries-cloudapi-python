from typing import Optional

from aries_cloudcontroller import IndyPresSpec, IndyProofRequest
from pydantic import BaseModel

from shared.models.protocol import PresentProofProtocolVersion


class CreateProofRequest(BaseModel):
    proof_request: IndyProofRequest
    auto_verify: Optional[bool] = None
    comment: Optional[str] = None
    trace: Optional[bool] = None
    protocol_version: PresentProofProtocolVersion


class SendProofRequest(CreateProofRequest):
    connection_id: str


class ProofId(BaseModel):
    proof_id: str


class AcceptProofRequest(ProofId):
    indy_presentation_spec: Optional[IndyPresSpec]


class RejectProofRequest(ProofId):
    problem_report: Optional[str] = None
