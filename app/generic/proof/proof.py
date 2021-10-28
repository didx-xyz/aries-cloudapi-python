import logging
from enum import Enum
from typing import Optional, Union

from aries_cloudcontroller import (
    AcaPyClient,
    AdminAPIMessageTracing,
    IndyPresSpec,
    IndyProofRequest,
    V10PresentationProposalRequest,
    V10PresentationSendRequestRequest,
    V20PresRequestByFormat,
    V20PresProposalRequest,
    V20PresSendRequestRequest,
)
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import agent_selector
from app.generic.proof.facades.acapy_proof_v1 import ProofsV1
from app.generic.proof.facades.acapy_proof_v2 import ProofsV2
from app.generic.proof.models import Presentation

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/generic/proof", tags=["proof"])


class ProofsFacade(Enum):
    v1 = ProofsV1
    v2 = ProofsV2


@router.post("/send-request")
async def send_proof_request(
    presentation_request: Union[
        V10PresentationSendRequestRequest,
        AdminAPIMessageTracing,
        V10PresentationProposalRequest,
        V20PresProposalRequest,
        V20PresSendRequestRequest,
    ],
    aries_controller: AcaPyClient = Depends(agent_selector),
) -> Presentation:
    """
    Send proof request.

    Parameters:
    -----------
    presentation_request:
        The proof request
    """
    v1_proof = await ProofsFacade.v1.value.send_proof_request(
        controller=aries_controller, presentation_request=presentation_request
    )
    v2_proof = await ProofsFacade.v2.value.send_proof_request(
        controller=aries_controller, presentation_request=presentation_request
    )
    return Presentation(V10=v1_proof, V20=v2_proof)


@router.post("/create-request")
async def create_proof_request(
    proof: Union[IndyProofRequest, V20PresRequestByFormat] = None,
    comment: Optional[str] = None,
    trace: Optional[bool] = False,
    aries_controller: AcaPyClient = Depends(agent_selector),
) -> Presentation:
    """
    Create proof request.

    Parameters:
    -----------
    proof: IndyProofRequest
        The proof request
    """
    try:
        proof = IndyProofRequest(**proof.dict())
        v1_proof = await ProofsFacade.v1.value.create_proof_request(
            controller=aries_controller, proof=proof, comment=comment, trace=trace
        )
        return Presentation(V10=v1_proof.V10)
    except TypeError:
        proof = V20PresRequestByFormat(**proof.dict())
        v2_proof = await ProofsFacade.v2.value.create_proof_request(
            controller=aries_controller, proof=proof
        )
        return Presentation(V20=v2_proof.V20)
    except TypeError:
        raise HTTPException(
            status_code=500,
            detail="Could not match provided type. Type needs to be IndyProofRequest or V20PresRequestByFormat",
        )


@router.get("/accept-request")
async def accept_proof_request(
    pres_ex_id: str,
    presentation_spec: Optional[IndyPresSpec],
    aries_controller: AcaPyClient = Depends(agent_selector),
) -> Presentation:
    """
    Accept proof request.

    Parameters:
    -----------
    pres_ex_id: str
        The presentation exchange ID
    presentation_spec: IndyPresSpec
        The presentation spec
    """
    v1_proof = await ProofsFacade.v1.value.accept_proof_request(
        controller=aries_controller,
        pres_ex_id=pres_ex_id,
        presentation_spec=presentation_spec,
    )

    v2_proof = await ProofsFacade.v2.value.accept_proof_request(
        controller=aries_controller,
        pres_ex_id=pres_ex_id,
        presentation_spec=presentation_spec,
    )

    return Presentation(V10=v1_proof.V10, V20=v2_proof.V20)


@router.get("/reject-request")
async def reject_proof_request(
    pres_ex_id: str,
    problem_report: Optional[str] = None,
    aries_controller: AcaPyClient = Depends(agent_selector),
) -> dict:
    """
    Reject proof request.

    Parameters:
    -----------
    pres_ex_id: str
        The presentation exchange ID
    problem_report: Optional[str]
        The problem report
    """
    v1_proof = ProofsFacade.v1.value.reject_proof_request(
        controller=aries_controller,
        pres_ex_id=pres_ex_id,
        problem_report=problem_report,
    )

    v2_proof = ProofsFacade.v2.value.reject_proof_request(
        controller=aries_controller,
        pres_ex_id=pres_ex_id,
        problem_report=problem_report,
    )

    return Presentation(V10=v1_proof.V10, V20=v2_proof.V20)
