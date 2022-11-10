from enum import Enum
from typing import Optional

from aries_cloudcontroller import (
    IndyPresSpec,
    IndyProofRequest,
)
from pydantic import BaseModel


class PresentProofProtocolVersion(Enum):
    v1: str = "v1"
    v2: str = "v2"


class SendProofRequest(BaseModel):
    connection_id: str
    proof_request: IndyProofRequest
    protocol_version: PresentProofProtocolVersion


class CreateProofRequest(BaseModel):
    proof_request: IndyProofRequest
    comment: Optional[str] = None
    protocol_version: PresentProofProtocolVersion


class AcceptProofRequest(BaseModel):
    proof_id: str
    presentation_spec: IndyPresSpec


class RejectProofRequest(BaseModel):
    proof_id: str
    problem_report: Optional[str] = None
