from typing import List, Optional
from uuid import UUID

from aries_cloudcontroller import IndyCredPrecis
from fastapi import APIRouter, Depends

from app.dependencies.acapy_clients import client_from_auth
from app.dependencies.auth import AcaPyAuth, acapy_auth_from_header
from app.exceptions import CloudApiException
from app.models.verifier import (
    AcceptProofRequest,
    CreateProofRequest,
    RejectProofRequest,
    SendProofRequest,
)
from app.util.acapy_verifier_utils import (
    VerifierFacade,
    assert_valid_prover,
    assert_valid_verifier,
    get_verifier_by_version,
)
from shared.log_config import get_logger
from shared.models.presentation_exchange import (
    PresentationExchange,
    Role,
    State,
    back_to_v1_presentation_state,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/verifier", tags=["verifier"])


@router.post("/create-request", response_model=PresentationExchange)
async def create_proof_request(
    body: CreateProofRequest,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> PresentationExchange:
    """
    Create proof request.
    ---------------------

    TODO: Add stuff about no connection_id and OOB

    Parameters:
    -----------
    body: CreateProofRequest
        The proof request object

    Returns:
    --------
    presentation_exchange: PresentationExchange
        The presentation exchange record
    """
    bound_logger = logger.bind(body=body)
    bound_logger.info("POST request received: Create proof request")

    try:
        verifier = get_verifier_by_version(body.protocol_version)

        async with client_from_auth(auth) as aries_controller:
            bound_logger.debug("Creating proof request")
            result = await verifier.create_proof_request(
                controller=aries_controller, create_proof_request=body
            )
    except Exception as e:
        bound_logger.info("Could not create presentation record: {}.", e)
        raise

    if result:
        bound_logger.info("Successfully created proof request.")
    else:
        bound_logger.warning("No result obtained from creating proof request.")
    return result


@router.post("/send-request", response_model=PresentationExchange)
async def send_proof_request(
    body: SendProofRequest,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> PresentationExchange:
    """
    Send proof request.
    -------------------
    Only a tenant with the verifier role can send a proof request.
    TODO mention something about type of proof request (diff or indy)

    Parameters:
    -----------
    body: SendProofRequest
        The proof request object

    Returns:
    --------
    presentation_exchange: PresentationExchange
        The presentation exchange record
    """
    bound_logger = logger.bind(body=body)
    bound_logger.info("POST request received: Send proof request")

    try:
        verifier = get_verifier_by_version(body.protocol_version)

        async with client_from_auth(auth) as aries_controller:
            if body.connection_id:
                await assert_valid_verifier(
                    aries_controller=aries_controller, proof_request=body
                )

            bound_logger.debug("Sending proof request")
            result = await verifier.send_proof_request(
                controller=aries_controller, send_proof_request=body
            )
    except CloudApiException as e:
        bound_logger.info("Could not send proof request: {}", e)
        raise

    if result:
        bound_logger.info("Successfully sent proof request.")
    else:
        bound_logger.warning("No result obtained from sending proof request.")
    return result


@router.post("/accept-request", response_model=PresentationExchange)
async def accept_proof_request(
    body: AcceptProofRequest,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> PresentationExchange:
    """
    Accept proof request.
    ---------------------

    A tenant responds to a proof request with this endpoint.


    Parameters:
    -----------
    body: AcceptProofRequest
        The proof request object

    Returns:
    --------
    presentation_exchange: PresentationExchange
        The presentation exchange record
    """
    bound_logger = logger.bind(body=body)
    bound_logger.info("POST request received: Accept proof request")

    try:
        verifier = get_verifier_by_version(body.proof_id)

        async with client_from_auth(auth) as aries_controller:
            bound_logger.debug("Get proof record")
            proof_record = await verifier.get_proof_record(
                controller=aries_controller, proof_id=body.proof_id
            )

            # If there is a connection id the proof is not connectionless
            if proof_record.connection_id:
                await assert_valid_prover(
                    aries_controller=aries_controller,
                    verifier=verifier,
                    presentation=body,
                )
            else:
                bound_logger.warning(
                    "No connection associated with proof. Skip validating prover"
                )

            bound_logger.debug("Accepting proof record")
            result = await verifier.accept_proof_request(
                controller=aries_controller, accept_proof_request=body
            )
    except CloudApiException as e:
        bound_logger.info("Could not accept proof request: {}", e)
        raise

    if result:
        bound_logger.info("Successfully accepted proof request.")
    else:
        bound_logger.warning("No result obtained from accepting proof request.")
    return result


@router.post("/reject-request", status_code=204)
async def reject_proof_request(
    body: RejectProofRequest,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> None:
    """
    Reject proof request.
    ---------------------
    TODO mention something about rejecting

    Parameters:
    -----------
    body: RejectProofRequest
        The proof request object

    Returns:
    --------
        None

    """
    bound_logger = logger.bind(body=body)
    bound_logger.info("POST request received: Reject proof request")

    try:
        verifier = get_verifier_by_version(body.proof_id)

        async with client_from_auth(auth) as aries_controller:
            bound_logger.debug("Getting proof record")
            proof_record = await verifier.get_proof_record(
                controller=aries_controller, proof_id=body.proof_id
            )

            if proof_record.state != "request-received":
                message = (
                    "Proof record must be in state `request-received` to reject; "
                    f"record has state: `{proof_record.state}`."
                )
                bound_logger.info(message)
                raise CloudApiException(message, 400)

            bound_logger.debug("Rejecting proof request")
            await verifier.reject_proof_request(
                controller=aries_controller, reject_proof_request=body
            )
    except CloudApiException as e:
        bound_logger.info("Could not reject request: {}.", e)
        raise

    bound_logger.info("Successfully rejected proof request.")


@router.get("/proofs", response_model=List[PresentationExchange])
async def get_proof_records(
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
    connection_id: Optional[str] = None,
    role: Optional[Role] = None,
    state: Optional[State] = None,
    thread_id: Optional[UUID] = None,
) -> List[PresentationExchange]:
    """
    Get all proof records
    ----------------------
    These records contains information about the proof request and the proof presentation.

    If a proof is sent by a verifier with 'save_exchange_record' set to False the record
    will be deleted after the exchange was completed.
    The tenant can filter the results by connection_id, role, state, and thread_id.

    Parameters:
    ----------
    connection_id: Optional[str]
    role: Optional[Role]: "prover", "verifier"
    state: Optional[State]: "abandoned", "done", "presentation-received",
                            "presentation-sent", "proposal-received", "proposal-sent",
                            "request-received", "request-sent"
    thread_id: Optional[UUID]

    Returns:
    --------
    presentation_exchange_list: [PresentationExchange]
        The list of presentation exchange records

    """
    logger.info("GET request received: Get all proof records")

    try:
        async with client_from_auth(auth) as aries_controller:
            logger.debug("Fetching v1 proof records")
            v1_records = await VerifierFacade.V1.value.get_proof_records(
                controller=aries_controller,
                connection_id=connection_id,
                role=role,
                state=back_to_v1_presentation_state(state) if state else None,
                thread_id=str(thread_id) if thread_id else None,
            )
            logger.debug("Fetching v2 proof records")
            v2_records = await VerifierFacade.V2.value.get_proof_records(
                controller=aries_controller,
                connection_id=connection_id,
                role=role,
                state=state,
                thread_id=str(thread_id) if thread_id else None,
            )
    except CloudApiException as e:
        logger.info("Could not fetch proof records: {}.", e)
        raise

    result = v1_records + v2_records
    if result:
        logger.info("Successfully fetched v1 and v2 records.")
    else:
        logger.info("No v1 or v2 records returned.")
    return result


@router.get("/proofs/{proof_id}", response_model=PresentationExchange)
async def get_proof_record(
    proof_id: str,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> PresentationExchange:
    """
    Get a specific proof record
    ---------------------------
    The tenant can get a specific proof record by providing the proof ID.

    If the proof was sent with 'save_exchange_record' set to False the
    record will not be available after the exchange was completed.
    A holder's records will always be deleted after the exchange was completed.

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
        verifier = get_verifier_by_version(version_candidate=proof_id)

        async with client_from_auth(auth) as aries_controller:
            bound_logger.debug("Fetching proof record")
            result = await verifier.get_proof_record(
                controller=aries_controller, proof_id=proof_id
            )
    except CloudApiException as e:
        logger.info("Could not fetch proof record: {}.", e)
        raise

    if result:
        bound_logger.info("Successfully fetched proof record.")
    else:
        bound_logger.info("No record returned.")
    return result


@router.delete("/proofs/{proof_id}", status_code=204)
async def delete_proof(
    proof_id: str,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> None:
    """
    Deletes a proof record
    -----------------------

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
        verifier = get_verifier_by_version(version_candidate=proof_id)

        async with client_from_auth(auth) as aries_controller:
            bound_logger.debug("Deleting proof record")
            await verifier.delete_proof(controller=aries_controller, proof_id=proof_id)
    except CloudApiException as e:
        bound_logger.info("Could not delete proof record: {}.", e)
        raise

    bound_logger.info("Successfully deleted proof record.")


@router.get("/proofs/{proof_id}/credentials", response_model=List[IndyCredPrecis])
async def get_credentials_by_proof_id(
    proof_id: str,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> List[IndyCredPrecis]:
    """
    Get matching credentials for presentation exchange
    ---------------------------------------------------
    Get matching credentials for a proof request by providing the proof ID.

    Returns a list of credential that the holder needs to respond to the proof request.
    The 'presentation_referents' field, for each object in this list, tells the holder which
    of the fields in the proof request that credential satisfies.

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
        verifier = get_verifier_by_version(version_candidate=proof_id)

        async with client_from_auth(auth) as aries_controller:
            bound_logger.debug("Fetching credentials for request")
            result = await verifier.get_credentials_by_proof_id(
                controller=aries_controller, proof_id=proof_id
            )
    except CloudApiException as e:
        bound_logger.info("Could not get matching credentials: {}.", e)
        raise

    bound_logger.info("Successfully fetched credentials for proof request.")
    return result
