from typing import List

from aries_cloudcontroller import IndyCredPrecis
from fastapi import APIRouter, Depends

from app.dependencies.acapy_clients import client_from_auth
from app.dependencies.auth import AcaPyAuth, acapy_auth
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
from shared.models.webhook_topics import PresentationExchange

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/verifier", tags=["verifier"])


@router.post("/create-request", response_model=PresentationExchange)
async def create_proof_request(
    body: CreateProofRequest,
    auth: AcaPyAuth = Depends(acapy_auth),
) -> PresentationExchange:
    """
    Creates a presentation request that is not bound to any specific proposal or connection.

    This endpoint facilitates the creation of a standalone presentation request. The generated request is
    not directly associated with any holder or connection at the time of creation, making it available for
    use in various contexts, such as submitting over the Out-Of-Band (OOB) protocol. This allows the
    presentation request to be utilized by any holder who can fulfil the criteria specified within it.

    Notably, the creation of a presentation request is not limited to verifiers. Any participant, including
    holders, can generate a request. This facilitates diverse interactions within the ecosystem, such as a
    holder creating a presentation request to engage with another holder. The flexibility of the approach
    supports a wide range of use cases, from traditional verification processes to peer exchanges and more.

    ### Parameters:
    body: CreateProofRequest
        The proof request object

    ### Returns:
    presentation_exchange: PresentationExchange
        The presentation exchange record

    ### Note
    For a detailed technical specification and informative diagrams related to the present proof process,
    refer to the [v1 Present Proof RFC](https://github.com/hyperledger/aries-rfcs/tree/main/features/0037-present-proof)
    and/or the [v2 Present Proof RFC](https://github.com/hyperledger/aries-rfcs/tree/main/features/0454-present-proof-v2).
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
    auth: AcaPyAuth = Depends(acapy_auth),
) -> PresentationExchange:
    """
    Send proof request.

    Parameters:
    -----------
    body: SendProofRequest
        The proof request object

    Returns:
    --------
    presentation_exchange: PresentationExchange
        The presentation exchange record

    ### Note
    For a detailed technical specification and informative diagrams related to the present proof process,
    refer to the [v1 Present Proof RFC](https://github.com/hyperledger/aries-rfcs/tree/main/features/0037-present-proof)
    and/or the [v2 Present Proof RFC](https://github.com/hyperledger/aries-rfcs/tree/main/features/0454-present-proof-v2).
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
    auth: AcaPyAuth = Depends(acapy_auth),
) -> PresentationExchange:
    """
    Accept proof request.

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
    auth: AcaPyAuth = Depends(acapy_auth),
) -> None:
    """
    Reject proof request.

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
                bound_logger.info(
                    "Proof record must be in state `request-received` to reject; had state: `{}`.",
                    proof_record.state,
                )
                raise CloudApiException(
                    "Record must be in state request-received to decline proof request.",
                    400,
                )

            bound_logger.debug("Rejecting proof request")
            await verifier.reject_proof_request(
                controller=aries_controller, reject_proof_request=body
            )
    except CloudApiException as e:
        bound_logger.info("Could not reject request: {}.", e)
        raise

    bound_logger.info("Successfully rejected proof request.")


@router.get(
    "/proofs",
    response_model=List[PresentationExchange],
    summary="Get Proof Exchange Records",
)
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
    except CloudApiException as e:
        logger.info("Could not fetch proof records: {}.", e)
        raise

    result = v1_records + v2_records
    if result:
        logger.info("Successfully fetched v1 and v2 records.")
    else:
        logger.info("No v1 or v2 records returned.")
    return result


@router.get(
    "/proofs/{proof_id}",
    response_model=PresentationExchange,
    summary="Get Proof Exchange Record",
)
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


@router.delete(
    "/proofs/{proof_id}", status_code=204, summary="Delete Proof Exchange Record"
)
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
        verifier = get_verifier_by_version(version_candidate=proof_id)

        async with client_from_auth(auth) as aries_controller:
            bound_logger.debug("Deleting proof record")
            await verifier.delete_proof(controller=aries_controller, proof_id=proof_id)
    except CloudApiException as e:
        bound_logger.info("Could not delete proof record: {}.", e)
        raise

    bound_logger.info("Successfully deleted proof record.")


@router.get(
    "/proofs/{proof_id}/credentials",
    response_model=List[IndyCredPrecis],
    summary="Get Matching Credentials by Proof ID",
)
async def get_credentials_by_proof_id(
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
