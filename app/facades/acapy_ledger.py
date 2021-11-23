import logging
from typing import Tuple

from aries_cloudcontroller import (
    AcaPyClient,
    CredentialDefinitionSendRequest,
    TAAAccept,
    TAAInfo,
    TAARecord,
)
from fastapi import HTTPException

import app.facades.acapy_wallet as wallet_facade
import app.facades.ledger as ledger_facade
from app.schemas import DidCreationResponse

logger = logging.getLogger(__name__)


async def get_taa(controller: AcaPyClient) -> Tuple[TAARecord, str]:
    """
    Obtains the TAA from the ledger

    Parameters:
    -----------
    controller: AcaPyClient
        The aries_cloudcontroller object

    Returns:
    --------
    taa: dict
        The TAA object
    """
    taa_response = await controller.ledger.fetch_taa()
    logger.info("taa_response:\n %s", taa_response)
    if isinstance(taa_response, TAAInfo) or isinstance(taa_response.result, TAAInfo):
        if taa_response.result:
            taa_response = taa_response.result
        mechanism = (
            taa_response.taa_accepted.mechanism
            if taa_response.taa_accepted
            else "service_agreement"
        )
        if not taa_response.taa_record and taa_response.taa_required:
            logger.error("Failed to get TAA:\n %s", taa_response)
            raise HTTPException(
                status_code=404,
                detail=f"Something went wrong. Could not get TAA. {taa_response}",
            )
        return taa_response, mechanism
    return taa_response, "service_agreement"


async def accept_taa(controller: AcaPyClient, taa: TAARecord, mechanism: str = None):
    """
    Accept the TAA

    Parameters:
    -----------
    controller: AcaPyClient
        The aries_cloudcontroller object
    TAA:
        The TAA object we want to agree to

    Returns:
    --------
    accept_taa_response: {}
        The response from letting the ledger know we accepted the response
    """
    accept_taa_response = await controller.ledger.accept_taa(
        body=TAAAccept(**taa.dict(), mechanism=mechanism)
    )
    logger.info("accept_taa_response: %s", accept_taa_response)
    if accept_taa_response != {}:
        logger.error("Failed to accept TAA.\n %s", accept_taa_response)
        raise HTTPException(
            status_code=404,
            detail=f"Something went wrong. Could not accept TAA. {accept_taa_response}",
        )
    return accept_taa_response


async def get_did_endpoint(controller: AcaPyClient, issuer_nym: str):
    """
    Obtains the public DID endpoint

    Parameters:
    -----------
    controller: AcaPyClient
        The aries_cloudcontroller object
    issuer_nym: str
        The issuer's Verinym

    Returns:
    --------
    issuer_endpoint_response: dict
        The response from getting the public endpoint associated with
        the issuer's Verinym from the ledger
    """
    issuer_endpoint_response = await controller.ledger.get_did_endpoint(did=issuer_nym)
    if not issuer_endpoint_response:
        logger.error("Failed to get DID endpoint:\n %s", issuer_endpoint_response)
        raise HTTPException(
            status_code=404,
            detail="Something went wrong. Could not obtain issuer endpoint.",
        )
    return issuer_endpoint_response


async def create_pub_did(
    aries_controller: AcaPyClient,
) -> DidCreationResponse:
    """
    Create a new public DID and
    write it to the ledger and
    receive its public info.
    Returns:
    * DID object (json)
    * Issuer verkey (str)
    * Issuer Endpoint (url)
    """
    did_object = await wallet_facade.create_did(aries_controller)
    await ledger_facade.post_to_ledger(did_object=did_object)

    taa_response, mechanism = await get_taa(aries_controller)
    if isinstance(taa_response, (TAAInfo, TAARecord)) and taa_response.taa_required:
        await accept_taa(
            aries_controller,
            taa_response.taa_record,
            mechanism,
        )
    await wallet_facade.assign_pub_did(aries_controller, did_object.did)
    get_pub_did_response = await wallet_facade.get_pub_did(aries_controller)
    issuer_nym = get_pub_did_response.result.did
    issuer_verkey = get_pub_did_response.result.verkey
    issuer_endpoint = await get_did_endpoint(aries_controller, issuer_nym)
    issuer_endpoint_url = issuer_endpoint.endpoint
    final_response = DidCreationResponse(
        did_object=get_pub_did_response.result,
        issuer_verkey=issuer_verkey,
        issuer_endpoint=issuer_endpoint_url,
    )
    return final_response


async def write_credential_def(controller: AcaPyClient, schema_id: str) -> str:
    """
    Writes Credential Definition to the ledger

    Parameters:
    ----------
    controller: AcaPyClient
        The aries_cloudcontroller object

    Schema id

    Returns:
    -------
    write_cred_response :dict
    """

    write_cred_response = await controller.credential_definition.publish_cred_def(
        body=CredentialDefinitionSendRequest(
            schema_id=schema_id, tag="default", support_revocation=False
        )
    )
    if not write_cred_response.credential_definition_id:
        raise HTTPException(
            status_code=404,
            detail="Something went wrong. Could not write credential definition to the ledger",
        )
    return write_cred_response.credential_definition_id
