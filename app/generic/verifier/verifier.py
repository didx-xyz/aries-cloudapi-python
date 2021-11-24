import logging
from enum import Enum
from typing import Literal

from aries_cloudcontroller import AcaPyClient
from fastapi import APIRouter, Depends

from app.dependencies import agent_selector
from app.generic.verifier.facades.acapy_verifier import Verifier
from app.generic.verifier.facades.acapy_verifier_v1 import VerifierV1
from app.generic.verifier.facades.acapy_verifier_v2 import VerifierV2
from app.generic.verifier.models import (
    AcceptProofRequest,
    CreateProofRequest,
    PresentationExchange,
    ProofRequestProtocolVersion,
    RejectProofRequest,
    SendProofRequest,
)

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/generic/verifier", tags=["verifier"])

ProtocolVersion = Literal[
    ProofRequestProtocolVersion.v10.value, ProofRequestProtocolVersion.v20.value
]


class VerifierFacade(Enum):
    v10 = VerifierV1
    v20 = VerifierV2


def __get_verifier_by_version(protocol_version: str) -> Verifier:
    if protocol_version == "v1":
        return VerifierFacade.v10.value
    elif protocol_version == "v2":
        return VerifierFacade.v20.value
    else:
        raise ValueError(f"Unknown protocol version {protocol_version}")


@router.post("/send-request")
async def send_proof_request(
    proof_request: SendProofRequest,
    aries_controller: AcaPyClient = Depends(agent_selector),
) -> PresentationExchange:
    """
    Send proof request.

    Parameters:
    -----------
    proof_request: SendProofRequest
        The proof request

    Returns:
    --------
    presentation_exchange: PresentationExchange
        The presentation exchange record
    """
    try:
        prover = __get_verifier_by_version(proof_request.protocol_version)
        return await prover.send_proof_request(
            controller=aries_controller, proof_request=proof_request
        )
    except Exception as e:
        logger.error(f"Failed to create presentation record: \n{e!r}")
        raise e from e


@router.post("/create-request")
async def create_proof_request(
    proof_request: CreateProofRequest,
    aries_controller: AcaPyClient = Depends(agent_selector),
) -> PresentationExchange:
    """
    Create proof request.

    Parameters:
    -----------
    proof_request: CreateProofRequest
        The proof request

    Returns:
    --------
    presentation_exchange: PresentationExchange
        The presentation exchange record
    """
    try:
        prover = __get_verifier_by_version(proof_request.protocol_version)
        return await prover.create_proof_request(
            controller=aries_controller, proof_request=proof_request
        )
    except Exception as e:
        logger.error(f"Failed to create presentation record: \n{e!r}")
        raise e from e


@router.post("/accept-request")
async def accept_proof_request(
    proof_request: AcceptProofRequest,
    aries_controller: AcaPyClient = Depends(agent_selector),
) -> PresentationExchange:
    """
    Accept proof request.

    Parameters:
    -----------
    proof_request: AcceptProofRequest
        The proof request

    Returns:
    --------
    presentation_exchange: PresentationExchange
        The presentation exchange record
    """
    try:
        prover = __get_verifier_by_version(proof_request.protocol_version)
        return await prover.accept_proof_request(
            controller=aries_controller, proof_request=proof_request
        )
    except Exception as e:
        logger.error(f"Failed to create presentation record: \n{e!r}")
        raise e from e


@router.post("/reject-request")
async def reject_proof_request(
    proof_request: RejectProofRequest,
    aries_controller: AcaPyClient = Depends(agent_selector),
) -> None:
    """
    Reject proof request.

    Parameters:
    -----------
    proof_request: RejectProofRequest
        The proof request

    Returns:
    --------
    presentation_exchange: PresentationExchange
        The presentation exchange record
    """
    try:
        prover = __get_verifier_by_version(proof_request.protocol_version)
        return await prover.reject_proof_request(
            controller=aries_controller, proof_request=proof_request
        )
    except Exception as e:
        logger.error(f"Failed to reject request: \n{e!r}")
        raise e from e
