import logging
from enum import Enum
from typing import Container, List

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
    RejectProofRequest,
    IndyCredPrecis,
    SendProofRequest,
)

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/generic/verifier", tags=["verifier"])


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


@router.get("/credentials")
async def get_credentials(
    pres_ex_id: str, aries_controller: AcaPyClient = Depends(agent_selector)
) -> List[IndyCredPrecis]:
    """
    Get matching credentials for  presentation exchange

    Parameters:
    ----------
    pres_ex_id: str
        The presentation exchange ID

    Returns:
    --------
    presentation_exchange_list: [IndyCredPrecis]
        The list of Indy presentation credentials
    """
    v1_creds = await VerifierFacade.v10.value.get_creds(
        pres_ex_id=pres_ex_id, controller=aries_controller
    )
    v2_creds = await VerifierFacade.v20.value.get_creds(
        pres_ex_id=pres_ex_id, controller=aries_controller
    )
    return [v1_creds, v2_creds]


@router.get("/proofs/")
async def get_all_proofs(
    aries_controller: AcaPyClient = Depends(agent_selector),
) -> List[PresentationExchange]:
    """
    Get all proofs for your wallet

    Parameters:
    ----------
    None

    Returns:
    --------
    presentation_exchange_list: [PresentationExchange]
        The list of presentation exchange records
    """
    v1_records = await VerifierFacade.v10.value.get_proof(controller=aries_controller)
    v2_records = await VerifierFacade.v20.value.get_proof(controller=aries_controller)
    return [v1_records, v2_records]


@router.get("/proofs")
async def get_all_proofs(
    aries_controller: AcaPyClient = Depends(agent_selector),
) -> List[PresentationExchange]:
    """
    Get all proofs for your wallet

    Parameters:
    ----------
    None

    Returns:
    --------
    presentation_exchange_list: [PresentationExchange]
        The list of presentation exchange records
    """
    v1_records = await VerifierFacade.v10.value.get_proof(controller=aries_controller)
    v2_records = await VerifierFacade.v20.value.get_proof(controller=aries_controller)
    return [v1_records, v2_records]


@router.get("/proofs/{pres_ex_id}")
async def get_proof(
    pres_ex_id: str, aries_controller: AcaPyClient = Depends(agent_selector)
) -> PresentationExchange:
    """
    Get proofs record for pres_ex_id

    Parameters:
    ----------
    pres_ex_id: str
        The presentation exchange ID

    Returns:
    --------
    presentation_exchange_list: PresentationExchange
        The of presentation exchange record for the proof ID
    """
    v1_records = await VerifierFacade.v10.value.get_proof(
        controller=aries_controller, pres_ex_id=pres_ex_id
    )
    v2_records = await VerifierFacade.v20.value.get_proof(
        controller=aries_controller, pres_ex_id=pres_ex_id
    )
    return [v1_records, v2_records]


@router.delete("/proofs/{pres_ex_id}")
async def delete_proof(
    pres_ex_id: str, aries_controller: AcaPyClient = Depends(agent_selector)
) -> List[None]:
    """
    Delete proofs record for pres_ex_id

    Parameters:
    ----------
    pres_ex_id: str

    Returns:
    --------
    None
    """
    v1_records = await VerifierFacade.v10.value.delete_proof(
        controller=aries_controller, pres_ex_id=pres_ex_id
    )
    v2_records = await VerifierFacade.v20.value.delete_proof(
        controller=aries_controller, pres_ex_id=pres_ex_id
    )
    return [v1_records, v2_records]


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
