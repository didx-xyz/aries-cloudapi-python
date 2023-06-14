from typing import Optional

from aries_cloudcontroller import IndyPresSpec, IndyProofRequest
from pydantic import BaseModel

from shared import PresentProofProtocolVersion


class SendProofRequest(BaseModel):
    connection_id: str
    proof_request: IndyProofRequest
    auto_verify: Optional[bool] = None
    comment: Optional[str] = None
    trace: Optional[bool] = None
    protocol_version: PresentProofProtocolVersion


class CreateProofRequest(BaseModel):
    proof_request: IndyProofRequest
    auto_verify: Optional[bool] = None
    comment: Optional[str] = None
    trace: Optional[bool] = None
    protocol_version: PresentProofProtocolVersion


class AcceptProofRequest(BaseModel):
    proof_id: str
    presentation_spec: IndyPresSpec


class RejectProofRequest(BaseModel):
    proof_id: str
    problem_report: Optional[str] = None
