from enum import Enum
from typing import Optional, Union

from aries_cloudcontroller import (
    IndyPresPreview,
    IndyPresSpec,
    IndyProofRequest,
)
from pydantic import BaseModel


class ProofRequestProtocolVersion(Enum):
    v10 = "v1"
    v20 = "v2"


class ProofRequestBase(BaseModel):
    protocol_version: Optional[str] = ProofRequestProtocolVersion.v10.value


class SendProofRequest(ProofRequestBase):
    connection_id: Optional[str] = None
    proof_request: Optional[Union[IndyProofRequest, IndyPresPreview]] = None


class CreateProofRequest(ProofRequestBase):
    proof_request: Optional[IndyProofRequest] = None
    comment: Optional[str] = None


class AcceptProofRequest(ProofRequestBase):
    proof_id: Optional[str] = None
    presentation_spec: Optional[IndyPresSpec] = None


class RejectProofRequest(ProofRequestBase):
    proof_id: Optional[str] = None
    problem_report: Optional[str] = None
