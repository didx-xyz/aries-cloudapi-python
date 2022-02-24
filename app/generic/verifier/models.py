from enum import Enum
from typing import Optional, Union

from aries_cloudcontroller import (
    IndyPresPreview,
    IndyPresSpec,
    IndyProofRequest,
)
from pydantic import BaseModel


class ProofRequestProtocolVersion(Enum):
    v1 = "v1"
    v2 = "v2"


class ProofRequestBase(BaseModel):
    protocol_version: Optional[str] = ProofRequestProtocolVersion.v1.value


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
<<<<<<< HEAD


class ProofRequestGeneric(ProofRequestBase):
    proof_id: str


class PresentationExchange(BaseModel):
    connection_id: Optional[str] = None
    created_at: str
    proof_id: str
    presentation: Optional[IndyProof] = None
    presentation_request: Optional[IndyProofRequest] = None
    protocol_version: ProofRequestProtocolVersion
    role: Literal["prover", "verifier"]
    state: Literal[
        "proposal-sent",
        "proposal-received",
        "request-sent",
        "request-received",
        "presentation-sent",
        "presentation-received",
        "done",
        "abandoned",
    ]
    updated_at: Optional[str] = None
    verified: Optional[bool] = None
=======
>>>>>>> development
