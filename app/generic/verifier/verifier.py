from typing import List

from aries_cloudcontroller import IndyCredPrecis
from fastapi import APIRouter, Depends

from app.config.log_config import get_logger
from app.dependencies.auth import AcaPyAuth, acapy_auth
from app.dependencies.role import client_from_auth
from app.exceptions.cloud_api_error import CloudApiException
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

logger = get_logger(__name__)

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
    bound_logger = logger.bind(body={"proof_id": proof_id})
    bound_logger.info("GET request received: Get credentials for a proof request")
    try:
        prover = get_verifier_by_version(version_candidate=proof_id)

        async with client_from_auth(auth) as aries_controller:
            bound_logger.debug("Fetching credentials for request")
            result = await prover.get_credentials_for_request(
                controller=aries_controller, proof_id=proof_id
            )
    except Exception as e:
        bound_logger.exception("Failed to get matching credentials.")
        raise e from e
    bound_logger.info("Successfully fetched credentials for proof request.")
    return result


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
    logger.info("GET request received: Get all proof records")
    try:
        async with client_from_auth(auth) as aries_controller:
            logger.debug("Fetching v1 proof records")
            v1_records = await VerifierFacade.v1.value.get_proof_records(
                controller=aries_controller
            )
            logger.debug("Fetching v2 proof records")
            v2_records = await VerifierFacade.v2.value.get_proof_records(
                controller=aries_controller
            )
    except Exception as e:
        logger.exception("Failed to get proof records.")
        raise e from e

    result = v1_records + v2_records
    if result:
        logger.info("Successfully fetched v1 and v2 records.")
    else:
        logger.info("No v1 or v2 records returned.")
    return result


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
    bound_logger = logger.bind(body={"proof_id": proof_id})
    bound_logger.info("GET request received: Get proof record by id")
    try:
        prover = get_verifier_by_version(version_candidate=proof_id)

        async with client_from_auth(auth) as aries_controller:
            bound_logger.debug("Fetching proof record")
            result = await prover.get_proof_record(
                controller=aries_controller, proof_id=proof_id
            )
    except Exception as e:
        bound_logger.exception("Failed to get proof record.")
        raise e from e

    if result:
        bound_logger.info("Successfully fetched proof record.")
    else:
        bound_logger.info("No record returned.")
    return result


@router.delete("/proofs/{proof_id}", status_code=204)
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
    bound_logger = logger.bind(body={"proof_id": proof_id})
    bound_logger.info("DELETE request received: Delete proof record by id")
    try:
        prover = get_verifier_by_version(version_candidate=proof_id)
        async with client_from_auth(auth) as aries_controller:
            bound_logger.debug("Deleting proof record")
            await prover.delete_proof(controller=aries_controller, proof_id=proof_id)
    except Exception as e:
        bound_logger.exception("Failed to delete proof record.")
        raise e from e
    bound_logger.info("Successfully deleted proof record.")


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
    bound_logger = logger.bind(body=proof_request)
    bound_logger.info("POST request received: Send proof request")
    try:
        prover = get_verifier_by_version(proof_request.protocol_version)

        async with client_from_auth(auth) as aries_controller:
            if proof_request.connection_id:
                await assert_valid_verifier(
                    aries_controller=aries_controller, proof_request=proof_request
                )

            bound_logger.debug("Sending proof request")
            result = await prover.send_proof_request(
                controller=aries_controller, proof_request=proof_request
            )
    except Exception as e:
        bound_logger.exception("Failed to send proof request.")
        raise e from e

    if result:
        bound_logger.info("Successfully sent proof request.")
    else:
        bound_logger.warning("No result obtained from senting proof request.")
    return result


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
    bound_logger = logger.bind(body=proof_request)
    bound_logger.info("POST request received: Create proof request")
    try:
        prover = get_verifier_by_version(proof_request.protocol_version)

        async with client_from_auth(auth) as aries_controller:
            bound_logger.debug("Creating proof request")
            result = await prover.create_proof_request(
                controller=aries_controller, proof_request=proof_request
            )
    except Exception as e:
        bound_logger.exception("Failed to create presentation record.")
        raise e from e

    if result:
        bound_logger.info("Successfully sent proof request.")
    else:
        bound_logger.warning("No result obtained from senting proof request.")
    return result


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
    bound_logger = logger.bind(body=presentation)
    bound_logger.info("POST request received: Accept proof request")
    try:
        prover = get_verifier_by_version(presentation.proof_id)

        async with client_from_auth(auth) as aries_controller:
            bound_logger.debug("Get proof record")
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

            bound_logger.debug("Accepting proof record")
            result = await prover.accept_proof_request(
                controller=aries_controller, proof_request=presentation
            )
    except Exception as e:
        bound_logger.exception("Failed to accept proof request.")
        raise e from e

    if result:
        bound_logger.info("Successfully accepted proof request.")
    else:
        bound_logger.warning("No result obtained from accepting proof request.")
    return result


@router.post("/reject-request", status_code=204)
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
    bound_logger = logger.bind(body=proof_request)
    bound_logger.info("POST request received: Reject proof request")
    try:
        prover = get_verifier_by_version(proof_request.proof_id)

        async with client_from_auth(auth) as aries_controller:
            bound_logger.debug("Getting proof record")
            proof_record = await prover.get_proof_record(
                controller=aries_controller, proof_id=proof_request.proof_id
            )

            if proof_record.state != "request-received":
                bound_logger.info(
                    "Proof record must be in state `request-received` to reject; had state: `{}`.",
                    proof_record.state,
                )
                raise CloudApiException(
                    "Record must be in state request-received to decline proof request",
                    400,
                )

            bound_logger.debug("Rejecting proof request")
            await prover.reject_proof_request(
                controller=aries_controller, proof_request=proof_request
            )
    except Exception as e:
        bound_logger.exception("Failed to reject request.")
        raise e from e

    bound_logger.info("Successfully rejected proof request.")
