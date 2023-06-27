import logging
from typing import List, Union

from aries_cloudcontroller import IndyCredPrecis
from dependency_injector.wiring import inject
from fastapi import APIRouter, Depends

from app.dependencies.acapy_client_roles_container import client_from_auth
from app.dependencies.auth import AcaPyAuth, acapy_auth
from app.generic.verifier.facades.acapy_verifier import Verifier
from app.generic.verifier.facades.acapy_verifier_utils import (
    VerifierFacade,
    assert_valid_prover,
    assert_valid_verifier,
)
from app.generic.verifier.models import (
    AcceptProofRequest,
    CreateProofRequest,
    RejectProofRequest,
    SendProofRequest,
)
from shared import PresentationExchange, PresentProofProtocolVersion
from shared.cloud_api_error import CloudApiException

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/generic/verifier", tags=["verifier"])


class VerifierFacade(Enum):
    v1 = VerifierV1
    v2 = VerifierV2


def __get_verifier_by_version(
    version_candidate: Union[str, PresentProofProtocolVersion]
) -> Verifier:
    if version_candidate == PresentProofProtocolVersion.v1 or (
        isinstance(version_candidate, str) and version_candidate.startswith("v1-")
    ):
        return VerifierFacade.v1.value
    elif (
        version_candidate == PresentProofProtocolVersion.v2
        or version_candidate.startswith("v2-")
    ):
        return VerifierFacade.v2.value
    else:
        raise ValueError(f"Unknown protocol version {version_candidate}")


@router.get("/proofs/{proof_id}/credentials", response_model=List[IndyCredPrecis])
async def get_credentials_for_request(
    proof_id: str,
    aries_controller: AcaPyClient = Depends(agent_selector),
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
        prover = __get_verifier_by_version(version_candidate=proof_id)
        return await prover.get_credentials_for_request(
            controller=aries_controller, proof_id=proof_id
        )
    except Exception as e:
        logger.error(f"Failed to get matching credentials: {proof_id} \n{e!r}")
        raise e from e


@router.get("/proofs", response_model=List[PresentationExchange])
async def get_proof_records(
    aries_controller: AcaPyClient = Depends(agent_selector),
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
    aries_controller: AcaPyClient = Depends(agent_selector),
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
        prover = __get_verifier_by_version(version_candidate=proof_id)
        return await prover.get_proof_record(
            controller=aries_controller, proof_id=proof_id
        )
    except Exception as e:
        logger.error(f"Failed to get proof records: \n{e!r}")
        raise e from e


@router.delete("/proofs/{proof_id}")
async def delete_proof(
    proof_id: str,
    aries_controller: AcaPyClient = Depends(agent_selector),
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
    aries_controller: AcaPyClient = Depends(agent_selector),
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
        prover = __get_verifier_by_version(proof_request.protocol_version)

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
    aries_controller: AcaPyClient = Depends(agent_selector),
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
        prover = __get_verifier_by_version(proof_request.protocol_version)

        return await prover.create_proof_request(
            controller=aries_controller, proof_request=proof_request
        )
    except Exception as e:
        logger.error(f"Failed to create presentation record: \n{e!r}")
        raise e from e


@router.post("/accept-request", response_model=PresentationExchange)
async def accept_proof_request(
    presentation: AcceptProofRequest,
    aries_controller: AcaPyClient = Depends(agent_selector),
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
        prover = __get_verifier_by_version(presentation.proof_id)

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
    aries_controller: AcaPyClient = Depends(agent_selector),
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
        prover = __get_verifier_by_version(proof_request.proof_id)
        proof_record = await prover.get_proof_record(
            controller=aries_controller, proof_id=proof_request.proof_id
        )

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
