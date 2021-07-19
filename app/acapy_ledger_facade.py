import logging

import acapy_wallet_facade as wallet_facade
import ledger_facade
from aries_cloudcontroller import AriesAgentControllerBase
from fastapi import HTTPException
from schemas import DidCreationResponse

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
    if "result" not in taa_response or not taa_response["result"]:
        logger.error("Failed to get TAA:\n{taa_response}")
        raise HTTPException(
            status_code=404,
            detail=f"Something went wrong. Could not get TAA. {taa_response}",
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
        logger.error(f"Failed to accept TAA.\n{accept_taa_response}")
        raise HTTPException(
            status_code=404,
            detail=f"Something went wrong. Could not accept TAA. {accept_taa_response}",
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
            detail=f"Something went wrong. Could not obtain issuer endpoint.",
        )
    return issuer_endpoint_response


async def create_pub_did(
    aries_controller: AriesAgentControllerBase = None,
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
    generate_did_res = await wallet_facade.create_did(aries_controller)
    did_object = generate_did_res["result"]
    await ledger_facade.post_to_ledger(did_object=did_object)

    taa_response = await get_taa(aries_controller)

    await accept_taa(aries_controller, taa_response)
    assign_pub_did = await wallet_facade.assign_pub_did(
        aries_controller, did_object["did"]
    )
    print(str(assign_pub_did))
    get_pub_did_response = await wallet_facade.get_pub_did(aries_controller)
    print(str(get_pub_did_response))
    issuer_nym = get_pub_did_response["result"]["did"]
    issuer_verkey = get_pub_did_response["result"]["verkey"]
    issuer_endpoint = await get_did_endpoint(aries_controller, issuer_nym)
    issuer_endpoint_url = issuer_endpoint["endpoint"]
    final_response = DidCreationResponse(
        did_object=get_pub_did_response["result"],
        issuer_verkey=issuer_verkey,
        issuer_endpoint=issuer_endpoint_url,
    )
    return final_response
