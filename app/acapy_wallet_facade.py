import logging

from aries_cloudcontroller import AcaPyClient
from fastapi import HTTPException

logger = logging.getLogger(__name__)


async def create_did(controller: AcaPyClient):
    """
    Creates a DID against the ledger using an AriesController

    Parameters:
    -----------
    controller: AriesController
        The aries_cloudcontroller object

    Returns:
    --------
    generate_did_response: dict
        The response object from generating a DID on the ledger
    """
    generate_did_res = await controller.wallet.create_did(body={})
    if not generate_did_res.result:
        logger.error("Failed to create DID:\n %s", generate_did_res)
        raise HTTPException(
            status_code=404,
            detail=f"Something went wrong.\nCould not generate DID.\n{generate_did_res}",
        )
    return generate_did_res.result


async def assign_pub_did(controller: AcaPyClient, did: str):
    """
    Assigns a publich did

    Parameters:
    -----------
    controller: AriesController
        The aries_cloudcontroller object
    did:
        the did as a base58 string

    Returns:
    --------
    assign_pub_did_response: dict
        The response obejct from assigning a a public did
    """
    assign_pub_did_response = await controller.wallet.set_public_did(did=did)
    logger.info("assign_pub_did_response:\n %s", assign_pub_did_response)
    if not assign_pub_did_response.result:
        logger.error("Failed to assign public DID:\n %s", assign_pub_did_response)
        raise HTTPException(
            status_code=500,
            detail=f"Something went wrong.\nCould not assign DID. {assign_pub_did_response}",
        )
    return assign_pub_did_response


async def get_pub_did(controller: AcaPyClient):
    """
    Obtains the public DID

    Parameters:
    -----------
    controller: AriesController
        The aries_cloudcontroller object

    Returns:
    --------
    get_pub_did_response: dict
        The response from getting the public DID from the ledger
    """
    get_pub_did_response = await controller.wallet.get_public_did()
    if not get_pub_did_response.result:
        logger.error("Failed to get public DID:\n %s", get_pub_did_response)
        raise HTTPException(
            status_code=404,
            detail=f"Something went wrong. Could not obtain public DID. {str(get_pub_did_response)}",
        )
    return get_pub_did_response
