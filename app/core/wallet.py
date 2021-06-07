import json

import logging

from distutils.util import strtobool
import requests
import os

import aries_cloudcontroller
from fastapi import HTTPException

from core import agent_factory
from core.delegates import ledger
from schemas import LedgerRequest, DidCreationResponse

logger = logging.getLogger(__name__)

is_multitenant = strtobool(os.getenv("IS_MULTITENANT", "False"))


async def create_public_did():
    """
    Create a new public DID and
    write it to the ledger and
    receive its public info.

    Returns:
    * DID object (json)
    * Issuer verkey (str)
    * Issuer Endpoint (url)
    """
    # TODO Can we break down this endpoint into smaller functions?
    # Because this really is too complex/too much happening at once.
    # This way not really testible/robust
    try:
        aries_agent_controller = agent_factory.create_aries_agentcontroller()
        # TODO: Should this come from env var or from the client request?
        # Adding empty header as parameters are being sent in payload
        generate_did_res = await aries_agent_controller.wallet.create_did()
        if not generate_did_res["result"]:
            raise HTTPException(
                # TODO: Should this return HTTPException, if so which status code?
                # Check same for occurences below
                status_code=404,
                detail=f"Something went wrong.\nCould not generate DID.\n{generate_did_res}",
            )
        did_object = generate_did_res["result"]
        await ledger.get_nym(did_object)
        taa_response = await aries_agent_controller.ledger.get_taa()
        logger.info(f"taa_response:\n{taa_response}")
        if not taa_response["result"]:
            error_json = taa_response.json()
            raise HTTPException(
                status_code=404,
                detail=f"Something went wrong. Could not get TAA. {error_json}",
            )
        TAA = taa_response["result"]["taa_record"]
        TAA["mechanism"] = "service_agreement"
        accept_taa_response = await aries_agent_controller.ledger.accept_taa(TAA)
        logger.info(f"accept_taa_response: {accept_taa_response}")
        if accept_taa_response != {}:
            error_json = accept_taa_response.json()
            raise HTTPException(
                status_code=404,
                detail=f"Something went wrong. Could not accept TAA. {error_json}",
            )
        assign_pub_did_response = await aries_agent_controller.wallet.assign_public_did(
            did_object["did"]
        )
        logger.info(f"assign_pub_did_response:\n{assign_pub_did_response}")
        if (
            not assign_pub_did_response["result"]
            or assign_pub_did_response["result"] == {}
        ):
            error_json = assign_pub_did_response.json()
            raise HTTPException(
                status_code=500,
                detail=f"Something went wrong.\nCould not assign DID. {error_json}",
            )
        get_pub_did_response = await aries_agent_controller.wallet.get_public_did()
        logger.info(f"get_pub_did_response:\n{get_pub_did_response}")
        if not get_pub_did_response["result"] or get_pub_did_response["result"] == {}:
            error_json = get_pub_did_response.json()
            raise HTTPException(
                status_code=404,
                detail=f"Something went wrong. Could not obtain public DID. {error_json}",
            )
        issuer_nym = get_pub_did_response["result"]["did"]
        issuer_verkey = get_pub_did_response["result"]["verkey"]
        issuer_endpoint = await aries_agent_controller.ledger.get_did_endpoint(
            issuer_nym
        )
        if not issuer_endpoint:
            raise HTTPException(
                status_code=404,
                detail="Something went wrong. Could not obtain issuer endpoint.",
            )
        issuer_endpoint_url = issuer_endpoint["endpoint"]
        final_response = DidCreationResponse(
            did_object=did_object,
            issuer_verkey=issuer_verkey,
            issuer_endpoint=issuer_endpoint_url,
        )
        await aries_agent_controller.terminate()
        return final_response
    except Exception as e:
        await aries_agent_controller.terminate()
        logger.error(f"The following error occured:\n{e!r}")
        raise HTTPException(
            status_code=500,
            detail=f"Something went wrong: {e!r}",
        ) from e


