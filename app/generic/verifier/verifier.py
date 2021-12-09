import logging
from enum import Enum
from typing import List

from aries_cloudcontroller import AcaPyClient, IndyCredPrecis
from fastapi import APIRouter, Depends

import app.generic.verifier.facades.acapy_verifier_utils as utils
from app.dependencies import agent_selector
from app.generic.verifier.facades.acapy_verifier import Verifier
from app.generic.verifier.facades.acapy_verifier_v1 import VerifierV1
from app.generic.verifier.facades.acapy_verifier_v2 import VerifierV2
from app.generic.verifier.models import (
    AcceptProofRequest,
    CreateProofRequest,
    PresentationExchange,
    RejectProofRequest,
    SendProofRequest,
    ProofRequestGeneric,
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


@router.post("/credentials")
async def get_credentials(
    proof_request: ProofRequestGeneric,
    aries_controller: AcaPyClient = Depends(agent_selector),
) -> List[IndyCredPrecis]:
    """
     Get matching credentials for  presentation exchange

     Parameters:
     ----------
    proof_request: ProofRequestGeneric
         The proof request object

     Returns:
     --------
     presentation_exchange_list: [IndyCredPrecis]
         The list of Indy presentation credentials
    """
    try:
        prover = __get_verifier_by_version(
            protocol_version=proof_request.protocol_version
        )
        return await prover.get_creds(
            controller=aries_controller, pres_ex_id=proof_request.proof_id
        )
    except Exception as e:
        logger.error(
            f"Failed to get matching credentials: \n {proof_request.proof_id}\n \n{e!r}"
        )
        raise e from e


@router.post("/proofs")
async def get_proofs(
    proof_request: ProofRequestGeneric,
    aries_controller: AcaPyClient = Depends(agent_selector),
) -> List[PresentationExchange]:
    """
    Get a specific proof record

    Parameters:
    ----------
    proof_request: ProofRequestGeneric
        The proof request object

    Returns:
    --------
    presentation_exchange_list: PresentationExchange
        The of presentation exchange record for the proof ID
    """
    try:
        prover = __get_verifier_by_version(
            protocol_version=proof_request.protocol_version
        )
        # If a proof ID os provided fetch a single record for tht ID
        if proof_request.proof_id:
            return await prover.get_proofs(
                controller=aries_controller, pres_ex_id=proof_request.proof_id
            )
        # Otherwise fecth all records for the wallet
        else:
            return await prover.get_proofs(controller=aries_controller)
    except Exception as e:
        logger.error(f"Failed to get proof(s): \n{e!r}")
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
        # Currently proof_id[0:2] is required for otherwise the protocol version is unknown
        # Maybe there is a better way to handle this?
        # Possibly also handling proof-di not starting with v1- or v2-?
        # Would it make sense to assume it is v1- by default/if none is supplied
        prover = __get_verifier_by_version(protocol_version=proof_id[0:2])
        pres_ex_id = utils.pres_id_no_version(proof_id)
        await prover.delete_proof(controller=aries_controller, pres_ex_id=pres_ex_id)
    except Exception as e:
        logger.error(f"Failed to delete proof record: \n{e!r}")
        raise e from e


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
        The proof request object

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
        The proof request object

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
        The proof request object

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
