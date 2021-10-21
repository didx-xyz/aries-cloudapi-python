from typing import Enum, Literal, Optional, Union

from aries_cloudcontroller import (
    IndyProof,
    IndyProofRequest,
    PresentationProposal,
    PresentationRequest,
    V20Pres,
    V20PresExRecordByFormat,
    V20PresProposal,
    V20PresRequest,
)
from generic.proof.proof import ProofsV1, ProofsV2
from pydantic import BaseModel


class ProofsFacade(Enum):
    v1 = ProofsV1
    v2 = ProofsV2


class Presentation(BaseModel):
    # both
    auto_present: Optional[bool] = None
    # V20 by_format
    by_format: Optional[V20PresExRecordByFormat] = None
    # both
    connection_id: Optional[str] = None
    created_at: Optional[str] = None
    error_msg: Optional[str] = None
    initiator: Optional[Literal["self", "external"]] = None
    # V20
    pres: Optional[V20Pres] = None
    pres_ex_id: Optional[str] = None
    pres_proposal: Optional[V20PresProposal] = None
    pres_request: Optional[V20PresRequest] = None
    # V10
    presentation: Optional[IndyProof] = None
    presentation_exchange_id: Optional[str] = None
    presentation_proposal_dict: Optional[PresentationProposal] = None
    presentation_request: Optional[IndyProofRequest] = None
    presentation_request_dict: Optional[PresentationRequest] = None
    # both
    role: Optional[Literal["prover", "verifier"]] = None
    # The below 'state' is a type hack to accomodate for v10 being not picky Optional[str]
    # and v20 being picky Literal[choices] but both versions sharing the same key
    state: Union[
        Optional[str],
        Optional[
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
        ],
    ] = None
    # both
    thread_id: Optional[str] = None
    trace: Optional[bool] = None
    updated_at: Optional[str] = None
    verified: Optional[Literal["true", "false"]] = None
