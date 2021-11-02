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
    V20PresSpecByFormatRequest,
)
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel

from app.dependencies import agent_selector
from app.generic.proof.facades.acapy_proof_v1 import ProofsV1
from app.generic.proof.facades.acapy_proof_v2 import ProofsV2
from app.generic.proof.models import Presentation

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/generic/proof", tags=["proof"])


class ProofsFacade(Enum):
    v1 = ProofsV1
    v2 = ProofsV2


class PresentationRequest(BaseModel):
    proof_request: Union[
        V10PresentationSendRequestRequest,
        AdminAPIMessageTracing,
        V10PresentationProposalRequest,
        V20PresProposalRequest,
        V20PresSendRequestRequest,
    ]


@router.post("/send-request")
async def send_proof_request(
    presentation_request: PresentationRequest,
    aries_controller: AcaPyClient = Depends(agent_selector),
) -> Presentation:
    """
    Send proof request.

    Parameters:
    -----------
    presentation_request:
        The proof request
    """

    async def _send_proof_request_v1(
        aries_controller,
        presentation_request,
        free: bool = False,
        pres_ex_id: str = None,
    ):
        return await ProofsFacade.v1.value.send_proof_request(
            controller=aries_controller,
            presentation_request=presentation_request,
            free=free,
            pres_ex_id=pres_ex_id,
        )

    async def _send_proof_request_v2(
        aries_controller,
        presentation_request,
        free: bool = False,
        pres_ex_id: str = None,
    ):
        return await ProofsFacade.v2.value.send_proof_request(
            controller=aries_controller,
            presentation_request=presentation_request,
            free=free,
            pres_ex_id=pres_ex_id,
        )

    v1_proof = None
    v2_proof = None
    if isinstance(presentation_request.proof_request, AdminAPIMessageTracing):
        v1_proof = await _send_proof_request_v1(
            aries_controller, presentation_request.proof_request
        )
        v2_proof = await _send_proof_request_v2(
            aries_controller, presentation_request.proof_request
        )
        return Presentation(V10=v1_proof, V20=v2_proof)
    elif isinstance(presentation_request.proof_request, V10PresentationProposalRequest):
        v1_proof = await _send_proof_request_v1(
            aries_controller, presentation_request.proof_request
        )
        return Presentation(V10=v1_proof)
    elif isinstance(
        presentation_request.proof_request, V10PresentationSendRequestRequest
    ):
        v1_proof = await _send_proof_request_v1(
            aries_controller, presentation_request.proof_request, free=True
        )
        return Presentation(V10=v1_proof)
    elif isinstance(
        presentation_request.proof_request, V20PresSendRequestRequest
    ) or isinstance(presentation_request.proof_request, V20PresProposalRequest):
        v2_proof = await _send_proof_request_v1(
            aries_controller, presentation_request.proof_request
        )
        return Presentation(V20=v2_proof)
    else:
        raise HTTPException(
            status_code=500,
            detail="Could not match provided type.",
        )


class CreateRequest(BaseModel):
    proof: Union[IndyProofRequest, V20PresRequestByFormat]


@router.post("/create-request")
async def create_proof_request(
    proof: CreateRequest,
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
    if isinstance(proof.proof, IndyProofRequest):
        v1_proof = await ProofsFacade.v1.value.create_proof_request(
            controller=aries_controller, proof=proof, comment=comment, trace=trace
        )
        return Presentation(V10=v1_proof.V10)
    elif isinstance(proof.proof, V20PresRequestByFormat):
        proof = V20PresRequestByFormat(**proof.dict())
        v2_proof = await ProofsFacade.v2.value.create_proof_request(
            controller=aries_controller, proof=proof
        )
        return Presentation(V20=v2_proof.V20)
    else:
        raise HTTPException(
            status_code=500,
            detail="Could not match provided type. Type needs to be IndyProofRequest or V20PresRequestByFormat",
        )


class AcceptRequest(BaseModel):
    presentation_spec: Union[V20PresSpecByFormatRequest, IndyPresSpec]


@router.post("/accept-request")
async def accept_proof_request(
    presentation_spec: AcceptRequest,
    pres_ex_id: str,
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
    return pres_ex_id
    if presentation_spec and presentation_spec.presentation_spec:
        if isinstance(presentation_spec.spec, IndyPresSpec):
            v1_proof = await ProofsFacade.v1.value.accept_proof_request(
                controller=aries_controller,
                pres_ex_id=pres_ex_id,
                presentation_spec=presentation_spec,
            )
            return Presentation(V10=v1_proof.V10)
        elif isinstance(
            presentation_spec.presentation_spec, V20PresSpecByFormatRequest
        ):
            v2_proof = await ProofsFacade.v2.value.accept_proof_request(
                controller=aries_controller,
                pres_ex_id=pres_ex_id,
                presentation_spec=presentation_spec,
            )
            return Presentation(V20=v2_proof.V20)
    elif not presentation_spec:
        v1_proof = await ProofsFacade.v1.value.accept_proof_request(
            controller=aries_controller,
            pres_ex_id=pres_ex_id,
        )
        # v2_proof = await ProofsFacade.v2.value.accept_proof_request(
        #     controller=aries_controller,
        #     pres_ex_id=pres_ex_id,
        # )
        # return Presentation(v10=v1_proof.V10,V20=v2_proof.V20)
        return Presentation(v10=v1_proof.V10)
    else:
        raise HTTPException(
            status_code=500,
            detail="Could not match provided type.",
        )


@router.post("/reject-request")
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
    # return Presentation(V10=v1_proof.V10)
    # return v1_proof
