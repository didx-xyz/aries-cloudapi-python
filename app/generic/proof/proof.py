import logging
from enum import Enum
from typing import Literal, Optional

from aries_cloudcontroller import (
    AcaPyClient,
    IndyPresSpec,
    IndyProofRequest,
    V10PresentationSendRequestRequest,
    V20PresRequestByFormat,
    V20PresSendRequestRequest,
    V20PresSpecByFormatRequest,
    V20PresProblemReportRequest,
)
from fastapi import APIRouter, Depends, HTTPException
from fastapi.param_functions import Body

from app.dependencies import agent_selector
from app.generic.proof.facades.acapy_proof_v1 import ProofsV1
from app.generic.proof.facades.acapy_proof_v2 import ProofsV2
from app.generic.proof.models import PresentationExchange

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/generic/proof", tags=["proof"])

ProtocolVersion = Literal["1", "2"]


class ProofsFacade(Enum):
    v10 = ProofsV1
    v20 = ProofsV2


@router.post("/send-request")
async def send_proof_request(
    connection_id: str,
    presentation_request: IndyProofRequest,
    protocol_version: Optional[ProtocolVersion] = "2",
    aries_controller: AcaPyClient = Depends(agent_selector),
) -> PresentationExchange:
    """
    Send proof request.

    Parameters:
    -----------
    presentation_request:
        The proof request
    """
    if protocol_version == "2":
        v2_presentation_exchange_rec = await ProofsFacade.v20.value.send_proof_request(
            controller=aries_controller,
            presentation_request=V20PresSendRequestRequest(
                connection_id=connection_id,
                presentation_request=V20PresRequestByFormat(
                    dif=None, indy=IndyProofRequest(**presentation_request.dict())
                ),
            ),
            free=True,  # alway set this to TRUE because we only support this for now.
        )
        return PresentationExchange(v10=None, v20=v2_presentation_exchange_rec)
    else:
        v1_presentation_exchange_rec = await ProofsFacade.v10.value.send_proof_request(
            controller=aries_controller,
            presentation_request=V10PresentationSendRequestRequest(
                connection_id=connection_id,
                proof_request=IndyProofRequest(**presentation_request.dict()),
            ),
            free=True,  # alway set this to TRUE because we only support this for now.
        )
        return PresentationExchange(v10=v1_presentation_exchange_rec, v20=None)


@router.post("/create-request")
async def create_proof_request(
    proof: IndyProofRequest,
    comment: Optional[str] = None,
    trace: Optional[bool] = False,
    protocol_version: Optional[ProtocolVersion] = "2",
    aries_controller: AcaPyClient = Depends(agent_selector),
) -> PresentationExchange:
    """
    Create proof request.

    Parameters:
    -----------
    proof: IndyProofRequest
        The proof request
    """
    if protocol_version == "2":
        v2_proof = await ProofsFacade.v20.value.create_proof_request(
            controller=aries_controller,
            proof=V20PresRequestByFormat(
                dif=None, indy=IndyProofRequest(**proof.dict())
            ),
            comment=comment,
            trace=trace,
        )
        return PresentationExchange(v10=None, v20=v2_proof)
    else:
        v1_proof = await ProofsFacade.v10.value.create_proof_request(
            controller=aries_controller,
            proof=IndyProofRequest(**proof.dict()),
            comment=comment,
            trace=trace,
        )
        return PresentationExchange(v10=v1_proof, v20=None)


@router.post("/accept-request")
async def accept_proof_request(
    presentation_spec: IndyPresSpec,
    pres_ex_id: str,
    protocol_version: Optional[ProtocolVersion] = "2",
    aries_controller: AcaPyClient = Depends(agent_selector),
) -> PresentationExchange:
    """
    Accept proof request.

    Parameters:
    -----------
    pres_ex_id: str
        The presentation exchange ID
    presentation_spec: IndyPresSpec
        The presentation spec
    """
    if protocol_version == "2":
        v2_presentation = await ProofsFacade.v20.value.accept_proof_request(
            controller=aries_controller,
            pres_ex_id=pres_ex_id,
            body=V20PresSpecByFormatRequest(
                dif=None, indy=IndyPresSpec(**presentation_spec.dict())
            ),
        )
        return PresentationExchange(v10=None, v20=v2_presentation)
    else:
        v1_presentation = await ProofsFacade.v10.value.accept_proof_request(
            controller=aries_controller,
            pres_ex_id=pres_ex_id,
            body=IndyPresSpec(**presentation_spec.dict()),
        )
        return PresentationExchange(v10=v1_presentation, v20=None)


@router.post("/reject-request")
async def reject_proof_request(
    pres_ex_id: str,
    problem_report: Optional[V20PresProblemReportRequest] = None,
    protocol_version: Optional[ProtocolVersion] = "2",
    aries_controller: AcaPyClient = Depends(agent_selector),
) -> None:
    """
    Reject proof request.

    Parameters:
    -----------
    pres_ex_id: str
        The presentation exchange ID
    problem_report: Optional[str]
        The problem report
    """
    try:
        if protocol_version == 2:
            await ProofsFacade.v10.value.reject_proof_request(
                controller=aries_controller,
                pres_ex_id=pres_ex_id,
                problem_report=problem_report,
            )
        else:
            await ProofsFacade.v20.value.reject_proof_request(
                controller=aries_controller,
                pres_ex_id=pres_ex_id,
                problem_report=problem_report,
            )
    except HTTPException as e:
        raise e from e
