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
)
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.dependencies import agent_selector
from app.generic.proof.facades.acapy_proof_v1 import ProofsV1
from app.generic.proof.facades.acapy_proof_v2 import ProofsV2
from app.generic.proof.models import PresentationExchange, ProofRequestProtocolVersion

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/generic/proof", tags=["proof"])

ProtocolVersion = Literal[
    ProofRequestProtocolVersion.v10.value, ProofRequestProtocolVersion.v20.value
]


class ProofRequestBase(BaseModel):
    protocol_version: Optional[str] = ProofRequestProtocolVersion.v10.value


class SendProofRequest(ProofRequestBase):
    connection_id: Optional[str] = None
    proof_request: Optional[IndyProofRequest] = None


class CreateProofRequest(ProofRequestBase):
    proof_request: Optional[IndyProofRequest] = None
    comment: Optional[str] = None


class AcceptProofRequest(ProofRequestBase):
    proof_id: Optional[str] = None
    presentation_spec: Optional[IndyPresSpec] = None


class RejectProofRequest(ProofRequestBase):
    proof_id: Optional[str] = None
    problem_report: Optional[str] = None


class ProofsFacade(Enum):
    v10 = ProofsV1
    v20 = ProofsV2


@router.post("/send-request")
async def send_proof_request(
    proof_request: SendProofRequest,
    aries_controller: AcaPyClient = Depends(agent_selector),
) -> PresentationExchange:
    """
    Send proof request.

    Parameters:
    -----------
    connection_id: str
        The connection id
    proof_request:
        The proof request
    protocol_version: Literal["v1", "v2"]
        The protocol version. default is 1

    Returns:
    --------
    presnetation_exchange: PresentationExchange
        The presentation exchange record
    """
    try:
        if proof_request.protocol_version == ProofRequestProtocolVersion.v20.value:
            presentation_exchange_rec = await ProofsFacade.v20.value.send_proof_request(
                controller=aries_controller,
                proof_request=V20PresSendRequestRequest(
                    connection_id=proof_request.connection_id,
                    presentation_request=V20PresRequestByFormat(
                        dif=None, indy=proof_request.proof_request
                    ),
                ),
            )
            return presentation_exchange_rec
        else:
            presentation_exchange_rec = await ProofsFacade.v10.value.send_proof_request(
                controller=aries_controller,
                proof_request=V10PresentationSendRequestRequest(
                    connection_id=proof_request.connection_id,
                    proof_request=proof_request.proof_request,
                ),
            )
        return presentation_exchange_rec
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
    proof: IndyProofRequest
        The proof request
    comment: Optional[str]
        A human-readable comment
    protocol_version: Literal["v1", "v2"]
        The protocol version. default is 1

    Returns:
    --------
    presnetation_exchange: PresentationExchange
        The presentation exchange record
    """
    try:
        if proof_request.protocol_version == ProofRequestProtocolVersion.v20.value:
            presentation_exchange = await ProofsFacade.v20.value.create_proof_request(
                controller=aries_controller,
                proof_request=V20PresRequestByFormat(
                    dif=None, indy=proof_request.proof_request
                ),
                comment=proof_request.comment,
            )
        else:
            presentation_exchange = await ProofsFacade.v10.value.create_proof_request(
                controller=aries_controller,
                proof_request=proof_request.proof_request,
                comment=proof_request.comment,
            )
        return presentation_exchange
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
    proof_id: str
        The presentation exchange ID
    presentation_spec: IndyPresSpec
        The presentation specification for Indy
    protocol_version: Literal["v1", "v2"]
        The protocol version. default is 1
    presentation_spec: IndyPresSpec
        The presentation spec

    Returns:
    --------
    presnetation_exchange: PresentationExchange
        The presentation exchange record
    """
    try:
        if proof_request.protocol_version == ProofRequestProtocolVersion.v20.value:
            presentation_exchange = await ProofsFacade.v20.value.accept_proof_request(
                controller=aries_controller,
                proof_id=proof_request.proof_id,
                body=V20PresSpecByFormatRequest(
                    dif=None, indy=proof_request.presentation_spec
                ),
            )
        else:
            presentation_exchange = await ProofsFacade.v10.value.accept_proof_request(
                controller=aries_controller,
                proof_id=proof_request.proof_id,
                body=proof_request.presentation_spec,
            )
        return presentation_exchange
    except Exception as e:
        logger.error(f"Failed to create presentation record: \n{e!r}")
        raise e from e


@router.post("/reject-request")
async def reject_proof_request(
    proof_request: RejectProofRequest,
    # proof_id: str,
    # problem_report: Optional[str] = None,
    # protocol_version: Optional[ProtocolVersion] = ProofRequestProtocolVersion.v10.value,
    aries_controller: AcaPyClient = Depends(agent_selector),
) -> None:
    """
    Reject proof request.

    Parameters:
    -----------
    proof_id: str
        The presentation exchange ID
    problem_report: Optional[str]
        The problem report

    Returns:
    --------
    presnetation_exchange: PresentationExchange
        The presentation exchange record
    """
    try:
        if proof_request.protocol_version == ProofRequestProtocolVersion.v20.value:
            await ProofsFacade.v20.value.reject_proof_request(
                controller=aries_controller,
                proof_id=proof_request.proof_id,
                problem_report=proof_request.problem_report,
            )
        else:
            await ProofsFacade.v10.value.reject_proof_request(
                controller=aries_controller,
                proof_id=proof_request.proof_id,
                problem_report=proof_request.problem_report,
            )
    except Exception as e:
        logger.error(f"Failed to reject request: \n{e!r}")
        raise e from e
