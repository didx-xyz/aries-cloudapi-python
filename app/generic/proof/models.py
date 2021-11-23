from enum import Enum
from typing import Dict, Optional, Literal, Union

from aries_cloudcontroller import (
    V20PresExRecordByFormat,
    V20Pres,
    IndyProof,
)
from pydantic import BaseModel


class ProofRequestProtocolVersion(Enum):
    v10 = "v1"
    v20 = "v2"


class PresentationExchange(BaseModel):
    connection_id: Optional[str] = None
    created_at: Optional[str] = None
    proof_id: str
    presentation: Optional[
        Union[IndyProof, V20Pres, V20PresExRecordByFormat, Dict]
    ] = None
    protocol_version: ProofRequestProtocolVersion
    role: Literal["prover", "verifier"]
    state: Optional[
        Literal[
            "proposal-sent",
            "proposal-received",
            "request-sent",
            "request-received",
            "presentation-sent",
            "presentation-received",
            "done",
            "abandoned",
        ]
    ] = None
    updated_at: Optional[str] = None
    verified: Optional[bool] = None
