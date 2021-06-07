from aries_cloudcontroller import AriesAgentController, AriesTenantController
from fastapi import Header, HTTPException
from contextlib import asynccontextmanager
import json
import requests
import os
import logging

admin_url = os.getenv("ACAPY_ADMIN_URL")
admin_port = os.getenv("ACAPY_ADMIN_PORT")
is_multitenant = os.getenv("IS_MULTITENANT", False)


logger = logging.getLogger(__name__)


@asynccontextmanager
async def create_controller(req_header: Header):
    """
    Instantiate an AriesAgentController or a TenantController
    based on header attributes

    Parameters:
    -----------
    req_header: Header
        The header object containing (wallet_id, jwt_token) or api_key

    Returns:
    --------
    controller: aries_cloudcontroller instance
        A generator of AriesAgentController or TenantController object
        (for use in contextmanager)
    """
    is_valid_header = req_header and (
        (("wallet_id" in req_header) and ("tenant_jwt" in req_header))
        or "api_key" in req_header
    )
    if is_valid_header:
        req_header = eval(req_header)
        if "api_key" in req_header:
            controller = AriesAgentController(
                admin_url=f"{admin_url}:{admin_port}",
                api_key=req_header["api_key"],
                is_multitenant=is_multitenant,
            )
        else:
            controller = AriesTenantController(
                admin_url=f"{admin_url}:{admin_port}",
                wallet_id=req_header["wallet_id"],
                tenant_jwt=req_header["tenant_jwt"],
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="Bad headers. Either provide an api_key or both wallet_id and tenant_jwt",
        )
    try:
        yield controller
    except Exception as e:
        logger.error(f"{e!r}")
        if e.status:
            raise HTTPException(
                status_code=e.status,
                detail=e.message,
            ) from e
        else:
            raise e
    finally:
        await controller.terminate()


async def create_did(controller):
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
    generate_did_res = await controller.wallet.create_did()
    if not generate_did_res["result"]:
        logger.error(f"Failed to create DID:\n{generate_did_res}")
        raise HTTPException(
            status_code=404,
            detail=f"Something went wrong.\nCould not generate DID.\n{generate_did_res}",
        )
    return generate_did_res


async def post_to_ledger(url, payload):
    """
    Post the did payload to the ledger

    Parameters:
    -----------
    url: str
        The url of the ledger to post to
    payload: dict
        The payload to be posted of the form:
        {"network": "stagingnet",
            "did": did_object["did"],
            "verkey": did_object["verkey"],
            "paymentaddr": "somestring",
        }

    Returns:
    --------
    post_to_ledger_resp: dict
        The response object of the post request
    """
    post_to_ledger_resp = requests.post(url, data=json.dumps(payload), headers={})
    if post_to_ledger_resp.status_code != 200:
        error_json = post_to_ledger_resp.json()
        logger.error(f"Failed to write to ledger:\n{error_json}")
        raise HTTPException(
            status_code=post_to_ledger_resp.status_code,
            detail=f"Something went wrong.\nCould not write to Ledger.\n{error_json}",
        )
    return post_to_ledger_resp


async def get_taa(controller):
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


async def accept_taa(controller, TAA):
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
    accept_taa_response = await controller.ledger.accept_taa(TAA)
    logger.info(f"accept_taa_response: {accept_taa_response}")
    if accept_taa_response != {}:
        error_json = accept_taa_response.json()
        logger.error(f"Failed to accept TAA.\n{error_json}")
        raise HTTPException(
            status_code=404,
            detail=f"Something went wrong. Could not accept TAA. {error_json}",
        )
    return accept_taa_response


async def assign_pub_did(controller, did_object):
    """
    Assigns a publich did

    Parameters:
    -----------
    controller: AriesController
        The aries_cloudcontroller object
    did_object:
        The DID response object from creating a did

    Returns:
    --------
    assign_pub_did_response: dict
        The response obejct from assigning a a public did
    """
    assign_pub_did_response = await controller.wallet.assign_public_did(
        did_object["did"]
    )
    logger.info(f"assign_pub_did_response:\n{assign_pub_did_response}")
    if not assign_pub_did_response["result"] or assign_pub_did_response["result"] == {}:
        error_json = assign_pub_did_response.json()
        logger.error(f"Failed to assign public DID:\n{error_json}")
        raise HTTPException(
            status_code=500,
            detail=f"Something went wrong.\nCould not assign DID. {error_json}",
        )
    return assign_pub_did_response


async def get_pub_did(controller):
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
    logger.info(f"get_pub_did_response:\n{get_pub_did_response}")
    if not get_pub_did_response["result"] or get_pub_did_response["result"] == {}:
        error_json = get_pub_did_response.json()
        logger.error(f"Failed to get public DID:\n{error_json}")
        raise HTTPException(
            status_code=404,
            detail=f"Something went wrong. Could not obtain public DID. {error_json}",
        )
    return get_pub_did_response


async def get_did_endpoint(controller, issuer_nym):
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
