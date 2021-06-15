import logging
from aries_cloudcontroller import AriesAgentControllerBase
from fastapi import HTTPException

logger = logging.getLogger(__name__)


async def get_taa(controller: AriesAgentControllerBase):
    """
    Obtains the TAA from the ledger

    Parameters:
    -----------
    controller: AriesController
        The aries_cloudcontroller object

    Returns:
    --------
    taa: dict
        The TAA object
    """
    taa_response = await controller.ledger.get_taa()
    logger.info(f"taa_response:\n{taa_response}")
    if not taa_response["result"]:
        error_json = taa_response.json()
        logger.error("Failed to get TAA:\n{error_json}")
        raise HTTPException(
            status_code=404,
            detail=f"Something went wrong. Could not get TAA. {error_json}",
        )
    taa = taa_response["result"]["taa_record"]
    taa["mechanism"] = "service_agreement"
    return taa


async def accept_taa(controller: AriesAgentControllerBase, taa):
    """
    Accept the TAA

    Parameters:
    -----------
    controller: AriesController
        The aries_cloudcontroller object
    TAA:
        The TAA object we want to agree to

    Returns:
    --------
    accept_taa_response: {}
        The response from letting the ledger know we accepted the response
    """
    accept_taa_response = await controller.ledger.accept_taa(taa)
    logger.info(f"accept_taa_response: {accept_taa_response}")
    if accept_taa_response != {}:
        error_json = accept_taa_response.json()
        logger.error(f"Failed to accept TAA.\n{error_json}")
        raise HTTPException(
            status_code=404,
            detail=f"Something went wrong. Could not accept TAA. {error_json}",
        )
    return accept_taa_response


async def get_did_endpoint(controller: AriesAgentControllerBase, issuer_nym):
    """
    Obtains the public DID endpoint

    Parameters:
    -----------
    controller: AriesController
        The aries_cloudcontroller object
    issuer_nym: str
        The issuer's Verinym

    Returns:
    --------
    issuer_endpoint_response: dict
        The response from getting the public endpoint associated with
        the issuer's Verinym from the ledger
    """
    issuer_endpoint_response = await controller.ledger.get_did_endpoint(issuer_nym)
    if not issuer_endpoint_response:
        logger.error(f"Failed to get DID endpoint:\n{issuer_endpoint_response}")
        raise HTTPException(
            status_code=404,
            detail=f"Something went wrong. Could not obtain issuer endpoint.{issuer_endpoint_response}",
        )
    return issuer_endpoint_response
