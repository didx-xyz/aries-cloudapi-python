from enum import Enum
from typing import Optional

from aries_cloudcontroller import (
    V10PresentationExchange,
    V20PresExRecord,
)
from pydantic import BaseModel


class ProofRequestProtocolVersion(Enum):
    v10 = "v1"
    v20 = "v2"


class PresentationExchange(BaseModel):
    v10: V10PresentationExchange = None
    v20: V20PresExRecord = None

    # # both
    # auto_present: Optional[bool] = None
    # # v2 only
    # by_format: Optional[V20PresExRecordByFormat] = None
    # # both
    # connection_id: Optional[str] = None
    # created_at: Optional[str] = None
    # error_msg: Optional[str] = None
    # initiator: Optional[Literal["self", "external"]] = None
    # # v2- specific
    # pres: Optional[V20Pres] = None
    # pres_ex_id: Optional[str] = None
    # pres_proposal: Optional[V20PresProposal] = None
    # pres_request: Optional[V20PresRequest] = None
    # # v1- specific
    # presentation: Optional[IndyProof] = None
    # presentation_exchange_id: Optional[str] = None
    # presentation_proposal_dict: Optional[PresentationProposal] = None
    # presentation_request: Optional[IndyProofRequest] = None
    # presentation_request_dict: Optional[PresentationRequest] = None
    # # both
    # role: Optional[Literal["prover", "verifier"]] = None
    # state: Optional[
    #     Literal[
    #         "proposal-sent",
    #         "proposal-received",
    #         "request-sent",
    #         "request-received",
    #         "presentation-sent",
    #         "presentation-received",
    #         "done",
    #         "abandoned",
    #     ]
    # ] = None
    # thread_id: Optional[str] = None
    # trace: Optional[bool] = None
    # updated_at: Optional[str] = None
    # verified: Optional[Literal["true", "false"]] = None
