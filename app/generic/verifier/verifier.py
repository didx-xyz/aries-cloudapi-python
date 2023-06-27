import logging
from typing import List

from aries_cloudcontroller import IndyCredPrecis
from fastapi import APIRouter, Depends

from app.dependencies.acapy_client_roles_container import client_from_auth
from app.dependencies.auth import AcaPyAuth, acapy_auth
from app.generic.verifier.facades.acapy_verifier_utils import (
    VerifierFacade,
    assert_valid_prover,
    assert_valid_verifier,
    get_verifier_by_version,
)
from app.generic.verifier.models import (
    AcceptProofRequest,
    CreateProofRequest,
    RejectProofRequest,
    SendProofRequest,
)
from shared import PresentationExchange
from shared.cloud_api_error import CloudApiException

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/generic/verifier", tags=["verifier"])


@router.get("/proofs/{proof_id}/credentials", response_model=List[IndyCredPrecis])
async def get_credentials_for_request(
    proof_id: str,
    auth: AcaPyAuth = Depends(acapy_auth),
) -> List[IndyCredPrecis]:
    """
    Get matching credentials for presentation exchange

    Parameters:
    ----------
    proof_id: str
         The proof ID

    Returns:
    --------
    presentation_exchange_list: [IndyCredPrecis]
        The list of Indy presentation credentials
    """
    try:
        prover = get_verifier_by_version(version_candidate=proof_id)
    except Exception as e:
        logger.error(f"Failed to get matching credentials: {proof_id} \n{e!r}")
        raise e from e


@router.get("/proofs", response_model=List[PresentationExchange])
async def get_proof_records(
    auth: AcaPyAuth = Depends(acapy_auth),
) -> List[PresentationExchange]:
    """
    Get all proof records

    Returns:
    --------
    presentation_exchange_list: [PresentationExchange]
        The list of presentation exchange records
    """
    try:
        v1_records = await VerifierFacade.v1.value.get_proof_records(
            controller=aries_controller
        )
        v2_records = await VerifierFacade.v2.value.get_proof_records(
            controller=aries_controller
        )
        return v1_records + v2_records
    except Exception as e:
        logger.error(f"Failed to get proof records: \n{e!r}")
        raise e from e


@router.get("/proofs/{proof_id}", response_model=PresentationExchange)
async def get_proof_record(
    proof_id: str,
    auth: AcaPyAuth = Depends(acapy_auth),
) -> PresentationExchange:
    """
    Get a specific proof record

    Parameters:
    ----------
    proof_id: str
        The proof ID

    Returns:
    --------
    presentation_exchange_record: PresentationExchange
        The of presentation exchange record for the proof ID
    """
    try:
        prover = get_verifier_by_version(version_candidate=proof_id)
    except Exception as e:
        logger.error(f"Failed to get proof records: \n{e!r}")
        raise e from e


@router.delete("/proofs/{proof_id}")
async def delete_proof(
    proof_id: str,
    auth: AcaPyAuth = Depends(acapy_auth),
) -> None:
    """
    Delete proofs record for proof_id (pres_ex_id including prepending version hint 'v1-' or 'v2-')

    Parameters:
    ----------
    proof_id: str
        The proof ID - starting with v1- or v2-

    Returns:
    --------
    None
    """
    try:
        prover = __get_verifier_by_version(version_candidate=proof_id)
        await prover.delete_proof(controller=aries_controller, proof_id=proof_id)
    except Exception as e:
        logger.error(f"Failed to delete proof record: \n{e!r}")
        raise e from e


@router.post("/send-request", response_model=PresentationExchange)
async def send_proof_request(
    proof_request: SendProofRequest,
    auth: AcaPyAuth = Depends(acapy_auth),
) -> PresentationExchange:
    """
    Send proof request.

    Parameters:
    -----------
    proof_request: SendProofRequest
        The proof request object

    Returns:
    --------
    presentation_exchange: PresentationExchange
        The presentation exchange record
    """
    try:
        prover = get_verifier_by_version(proof_request.protocol_version)

        if proof_request.connection_id:
            await assert_valid_verifier(
                aries_controller=aries_controller, proof_request=proof_request
            )

        return await prover.send_proof_request(
            controller=aries_controller, proof_request=proof_request
        )
    except Exception as e:
        logger.error(f"Failed to send proof request: \n{e!r}")
        raise e from e


@router.post("/create-request", response_model=PresentationExchange)
async def create_proof_request(
    proof_request: CreateProofRequest,
    auth: AcaPyAuth = Depends(acapy_auth),
) -> PresentationExchange:
    """
    Create proof request.

    Parameters:
    -----------
    proof_request: CreateProofRequest
        The proof request object

    Returns:
    --------
    presentation_exchange: PresentationExchange
        The presentation exchange record
    """
    try:
        prover = get_verifier_by_version(proof_request.protocol_version)

        return await prover.create_proof_request(
            controller=aries_controller, proof_request=proof_request
        )
    except Exception as e:
        logger.error(f"Failed to create presentation record: \n{e!r}")
        raise e from e


@router.post("/accept-request", response_model=PresentationExchange)
async def accept_proof_request(
    presentation: AcceptProofRequest,
    auth: AcaPyAuth = Depends(acapy_auth),
) -> PresentationExchange:
    """
    Accept proof request.

    Parameters:
    -----------
    proof_request: AcceptProofRequest
        The proof request object

    Returns:
    --------
    presentation_exchange: PresentationExchange
        The presentation exchange record
    """
    try:
        prover = get_verifier_by_version(presentation.proof_id)

        proof_record = await prover.get_proof_record(
            controller=aries_controller, proof_id=presentation.proof_id
        )

        # If there is a connection id the proof is not connectionless
        if proof_record.connection_id:
            await assert_valid_prover(
                aries_controller=aries_controller,
                prover=prover,
                presentation=presentation,
            )

        return await prover.accept_proof_request(
            controller=aries_controller, proof_request=presentation
        )
    except Exception as e:
        logger.error(f"Failed to accept proof request: \n{e!r}")
        raise e from e


@router.post("/reject-request")
async def reject_proof_request(
    proof_request: RejectProofRequest,
    auth: AcaPyAuth = Depends(acapy_auth),
) -> None:
    """
    Reject proof request.

    Parameters:
    -----------
    proof_request: RejectProofRequest
        The proof request object

    Returns:
    --------
    None
    """
    try:
        prover = get_verifier_by_version(proof_request.proof_id)

        if proof_record.state != "request-received":
            raise CloudApiException(
                "Record must be in state request-received to decline proof request", 400
            )

        return await prover.reject_proof_request(
            controller=aries_controller, proof_request=proof_request
        )
    except Exception as e:
        logger.error(f"Failed to reject request: \n{e!r}")
        raise e from e
