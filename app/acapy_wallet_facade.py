import logging

from aries_cloudcontroller import AriesAgentControllerBase
from fastapi import HTTPException

from api import DIDResult

logger = logging.getLogger(__name__)


async def create_did(controller: AriesAgentControllerBase):
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
    generate_did_res = await controller.wallet.create_default_did()
    # if "result" not in generate_did_res or not generate_did_res["result"]:
    #     logger.error(f"Failed to create DID:\n{generate_did_res}")
    #     raise HTTPException(
    #         status_code=404,
    #         detail=f"Something went wrong.\nCould not generate DID.\n{generate_did_res}",
    #     )
    return generate_did_res


async def assign_pub_did(controller: AriesAgentControllerBase, did: str):
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
    assign_pub_did_response = await controller.wallet.assign_public_did(did)
    logger.info(f"assign_pub_did_response:\n{assign_pub_did_response}")
    return assign_pub_did_response


async def get_pub_did(controller: AriesAgentControllerBase) -> DIDResult:
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
    return get_pub_did_response
