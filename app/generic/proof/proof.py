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
    proof_request: IndyProofRequest,
    protocol_version: Optional[ProtocolVersion] = "1",
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
    protocol_version: Literal["1", "2"]
        The protocol version. default is 1

    Returns:
    --------
    presnetation_exchange: PresentationExchange
        The presentation exchange record
    """
    try:
        if protocol_version == "2":
            presentation_exchange_rec = await ProofsFacade.v20.value.send_proof_request(
                controller=aries_controller,
                proof_request=V20PresSendRequestRequest(
                    connection_id=connection_id,
                    presentation_request=V20PresRequestByFormat(
                        dif=None, indy=IndyProofRequest(**proof_request.dict())
                    ),
                ),
                free=True,  # alway set this to TRUE because we only support this for now.
            )
            return presentation_exchange_rec
        else:
            presentation_exchange_rec = await ProofsFacade.v10.value.send_proof_request(
                controller=aries_controller,
                proof_request=V10PresentationSendRequestRequest(
                    connection_id=connection_id,
                    proof_request=IndyProofRequest(**proof_request.dict()),
                ),
                free=True,  # alway set this to TRUE because we only support this for now.
            )
        return presentation_exchange_rec
    except Exception as e:
        logger.error(f"Failed to create presentation record: \n{e!r}")
        raise e from e


@router.post("/create-request")
async def create_proof_request(
    proof_request: IndyProofRequest,
    comment: Optional[str] = None,
    trace: Optional[bool] = False,
    protocol_version: Optional[ProtocolVersion] = "1",
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
    trace: bool
        Whether to enable exchange tracing
    protocol_version: Literal["1", "2"]
        The protocol version. default is 1

    Returns:
    --------
    presnetation_exchange: PresentationExchange
        The presentation exchange record
    """
    try:
        if protocol_version == "2":
            presentation_exchange = await ProofsFacade.v20.value.create_proof_request(
                controller=aries_controller,
                proof_request=V20PresRequestByFormat(
                    dif=None, indy=IndyProofRequest(**proof_request.dict())
                ),
                comment=comment,
                trace=trace,
            )
        else:
            presentation_exchange = await ProofsFacade.v10.value.create_proof_request(
                controller=aries_controller,
                proof_request=IndyProofRequest(**proof_request.dict()),
                comment=comment,
                trace=trace,
            )
        return presentation_exchange
    except Exception as e:
        logger.error(f"Failed to create presentation record: \n{e!r}")
        raise e from e


@router.post("/accept-request")
async def accept_proof_request(
    pres_ex_id: str,
    presentation_spec: IndyPresSpec,
    protocol_version: Optional[ProtocolVersion] = "1",
    aries_controller: AcaPyClient = Depends(agent_selector),
) -> PresentationExchange:
    """
    Accept proof request.

    Parameters:
    -----------
    pres_ex_id: str
        The presentation exchange ID
    presentation_spec: IndyPresSpec
        The presentation specification for Indy
    protocol_version: Literal["1", "2"]
        The protocol version. default is 1
    presentation_spec: IndyPresSpec
        The presentation spec

    Returns:
    --------
    presnetation_exchange: PresentationExchange
        The presentation exchange record
    """
    try:
        pres_spec = IndyPresSpec(**presentation_spec.dict())
        if protocol_version == "2":
            presentation_exchange = await ProofsFacade.v20.value.accept_proof_request(
                controller=aries_controller,
                pres_ex_id=pres_ex_id,
                body=V20PresSpecByFormatRequest(dif=None, indy=pres_spec),
            )
        else:
            presentation_exchange = await ProofsFacade.v10.value.accept_proof_request(
                controller=aries_controller, pres_ex_id=pres_ex_id, body=pres_spec
            )
        return presentation_exchange
    except Exception as e:
        logger.error(f"Failed to create presentation record: \n{e!r}")
        raise e from e


@router.post("/reject-request")
async def reject_proof_request(
    pres_ex_id: str,
    problem_report: Optional[str] = None,
    protocol_version: Optional[ProtocolVersion] = "1",
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

    Returns:
    --------
    presnetation_exchange: PresentationExchange
        The presentation exchange record
    """
    try:
        if protocol_version == "2":
            await ProofsFacade.v20.value.reject_proof_request(
                controller=aries_controller,
                pres_ex_id=pres_ex_id,
                problem_report=problem_report,
            )
        else:
            await ProofsFacade.v10.value.reject_proof_request(
                controller=aries_controller,
                pres_ex_id=pres_ex_id,
                problem_report=problem_report,
            )
    except Exception as e:
        logger.error(f"Failed to reject request: \n{e!r}")
        raise e from e
