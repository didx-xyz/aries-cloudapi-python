import logging
from enum import Enum
from typing import Optional, Union, Tuple

from aries_cloudcontroller import AcaPyClient
from aries_cloudcontroller.model.indy_proof_request import IndyProofRequest
from aries_cloudcontroller.model.v10_presentation_create_request_request import (
    AdminAPIMessageTracing,
    V10PresentationSendRequestRequest,
    V10PresentationProposalRequest,
    V10PresentationExchange,
    V20PresentationExchange,
    IndyPresSpec,
)
from fastapi import APIRouter
from generic.proof.models import Presentation
from generic.proof.facades.acapy_proof_v1 import ProofsV1
from generic.proof.facades.acapy_proof_v2 import ProofsV2

from generic.proof.proof import ProofsV1, ProofsV2

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/generic/proof/", tags=["proof"])


class ProofsFacade(Enum):
    v1 = ProofsV1
    v2 = ProofsV2


@router.post("/send-request")
async def send_proof_request(
    presentation_request: Union[
        V10PresentationSendRequestRequest,
        AdminAPIMessageTracing,
        V10PresentationProposalRequest,
    ],
    aries_controller: AcaPyClient,
) -> Tuple[V10PresentationExchange, V20PresentationExchange]:
    """
    Send proof request.

    Parameters:
    -----------
    presentation_request:
        The proof request
    """
    v1_proof = await ProofsFacade.v1.send_proof_request(
        controller=aries_controller, presentation_request=presentation_request
    )

    v2_proof = await ProofsFacade.v2.send_proof_request(
        controller=aries_controller, presentation_request=presentation_request
    )

    return v1_proof, v2_proof


@router.post("/create-request")
async def create_proof_request(
    aries_controller: AcaPyClient,
    proof: IndyProofRequest,
    comment: Optional[str],
    trace: Optional[bool] = False,
) -> Tuple[V10PresentationExchange, V20PresentationExchange]:
    """
    Create proof request.

    Parameters:
    -----------
    proof: IndyProofRequest
        The proof request
    """
    v1_proof = await ProofsFacade.v1.create_proof_request(
        controller=aries_controller, proof=proof, comment=comment, trace=trace
    )

    v2_proof = await ProofsFacade.v2.create_proof_request(
        controller=aries_controller, proof=proof
    )

    return v1_proof, v2_proof


@router.get("/accept-request")
async def accept_proof_request(
    aries_controller: AcaPyClient,
    pres_ex_id: str,
    presentation_spec: Optional[IndyPresSpec],
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
    v1_proof = await ProofsFacade.v1.accept_proof_request(
        controller=aries_controller,
        pres_ex_id=pres_ex_id,
        presentation_spec=presentation_spec,
    )

    v2_proof = await ProofsFacade.v2.accept_proof_request(
        controller=aries_controller,
        pres_ex_id=pres_ex_id,
        presentation_spec=presentation_spec,
    )

    return v1_proof, v2_proof


@router.get("/reject-request")
async def reject_proof_request(
    aries_controller: AcaPyClient, pres_ex_id: str, problem_report: Optional[str] = None
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
    v1_proof = ProofsFacade.v1.reject_proof_request(
        controller=aries_controller,
        pres_ex_id=pres_ex_id,
        problem_report=problem_report,
    )

    v2_proof = ProofsFacade.v2.reject_proof_request(
        controller=aries_controller,
        pres_ex_id=pres_ex_id,
        problem_report=problem_report,
    )

    return v1_proof, v2_proof
