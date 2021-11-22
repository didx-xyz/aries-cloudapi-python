from enum import Enum
from typing import Dict, Optional, Literal, Union

from aries_cloudcontroller import (
    V10PresentationExchange,
    V20PresExRecord,
    V20PresExRecordByFormat,
    V20Pres,
    IndyProof,
    V20PresProposal,
    V20PresRequest,
    PresentationProposal,
    IndyProofRequest,
    PresentationRequest,
)
from pydantic import BaseModel


class ProofRequestProtocolVersion(Enum):
    v10 = "v1"
    v20 = "v2"


class PresentationExchange(BaseModel):
    # v10: V10PresentationExchange = None
    # v20: V20PresExRecord = None

    # # both
    auto_present: bool
    # # v2 only # proof attachment IndyProofRewuest "pres"
    # by_format: Optional[V20PresExRecordByFormat] = None
    # # both
    connection_id: Optional[str] = None
    created_at: Optional[str] = None
    # error_msg: Optional[str] = None
    initiator: Literal["self", "external"]
    # override for both
    # rename proof id with prefix
    presentation_exchange_id: str

    # # v2- specific
    # pres: Optional[V20Pres] = None
    # pres_ex_id: Optional[str] = None
    # pres_proposal: Optional[V20PresProposal] = None
    # pres_request: Optional[V20PresRequest] = None
    # v1- specific
    # IndyProof -> proof?
    presentation: Optional[
        Union[IndyProof, V20Pres, V20PresExRecordByFormat, Dict]
    ] = None
    # presentation: Optional[IndyProof] = None
    # presentation_exchange_id: Optional[str] = None
    # presentation_proposal_dict: Optional[PresentationProposal] = None
    # presentation_request: Optional[IndyProofRequest] = None
    # presentation_request_dict: Optional[PresentationRequest] = None
    # # both
    role: Literal["prover", "verifier"]  # = None
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
    # thread_id: Optional[str] = None
    # trace: Optional[bool] = None
    updated_at: Optional[str] = None
    # to bool not optional
    verified: Optional[bool] = None
