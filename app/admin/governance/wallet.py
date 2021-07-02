import logging
import json
import os
import traceback
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Depends

import ledger_facade
from schemas import (
    DidCreationResponse,
    InitWalletRequest,
)
from aries_cloudcontroller import AriesAgentControllerBase
from facade import yoma_agent, member_admin_agent

import acapy_ledger_facade
import acapy_wallet_facade

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wallets", tags=["wallets"])

# TODO Should the admin_api_key be a dummy variable so the controller doesn't function w/o providing it?
# This all smells really - this has to be done in a better manner


@router.get("/create-pub-did", tags=["did"], response_model=DidCreationResponse)
async def create_public_did(
    aries_controller: AriesAgentControllerBase = Depends(yoma_agent),
) -> DidCreationResponse:
    """
    Create a new public DID and
    write it to the ledger and
    receive its public info.

    Parameters:
    -----------
    api_key: Header(None)
        The request header object api_key
    wallet_id: Header(None)
        The request header object wallet_id
    tenant_jwt: Header(None)
        The request header object tenant_jwt

    Returns:
    * DID object (json)
    * Issuer verkey (str)
    * Issuer Endpoint (url)
    """

    generate_did_res = await acapy_wallet_facade.create_did(aries_controller)
    did_object = generate_did_res["result"]
    await ledger_facade.post_to_ledger(did_object=did_object)

    taa_response = await acapy_ledger_facade.get_taa(aries_controller)

    await acapy_ledger_facade.accept_taa(aries_controller, taa_response)
    await acapy_wallet_facade.assign_pub_did(aries_controller, did_object["did"])
    get_pub_did_response = await acapy_wallet_facade.get_pub_did(aries_controller)
    issuer_nym = get_pub_did_response["result"]["did"]
    issuer_verkey = get_pub_did_response["result"]["verkey"]
    issuer_endpoint = await acapy_ledger_facade.get_did_endpoint(
        aries_controller, issuer_nym
    )
    issuer_endpoint_url = issuer_endpoint["endpoint"]
    final_response = DidCreationResponse(
        did_object=get_pub_did_response["result"],
        issuer_verkey=issuer_verkey,
        issuer_endpoint=issuer_endpoint_url,
    )
    return final_response


@router.get("/")
async def wallets_root():
    """
    The default endpoints for wallets
    """
    # TODO: Determine what this should return or
    # whether this should return anything at all
    return {
        "message": "Wallets endpoint. Please, visit /docs to consult the Swagger docs."
    }


# TODO: This should be somehow retsricted?!
@router.post("/create-wallet")
async def create_wallet(
    aries_controller: AriesAgentControllerBase = Depends(member_admin_agent),
):
    """
    Create a new wallet

    Parameters:
    -----------
    wallet_payload: dict
        The payload for creating the wallet


    Returns:
    --------
    The response object from creating a wallet on the ledger

    Example Request Body:
    {
            "image_url": "https://aries.ca/images/sample.png",
            "key_management_mode": "managed",
            "label": "YOMA",
            "wallet_dispatch_type": "default",
            "wallet_key": "MySecretKey1234",
            "wallet_name": "YOMAsWallet",
            "wallet_type": "indy",
        }
    """

    # TODO Remove this default wallet. This has to be provided
    # At least unique values for eg label, The rest could be filled
    # with default values like image_url could point to a defautl avatar img
    # if not wallet_payload:
    payload = {
        "image_url": "https://aries.ca/images/sample.png",
        "key_management_mode": "managed",
        "label": "YOMA",
        "wallet_dispatch_type": "default",
        "wallet_key": "MySecretKey1234",
        "wallet_name": "YOMAsWallet",
        "wallet_type": "indy",
    }
    # else:
    # payload = wallet_payload

    wallet_response = await aries_controller.multitenant.create_subwallet(payload)

    return wallet_response
    # else:
    #     # TODO: Implement wallet_response as schema if that is useful
    #     wallet_response = await controller.wallet.create_did()
    # return wallet_response


@router.get("/remove-wallet")
async def remove_wallet_by_id(
    wallet_id: str, aries_controller: AriesAgentControllerBase = Depends(yoma_agent)
):

    response = await aries_controller.multitenant.remove_subwallet_by_id(wallet_id)
    # Should this be success or the response??
    if response:
        return print("Success")


@router.get("/get-subwallet-auth-token")
async def get_subwallet_auth_token(
    wallet_id: str, aries_controller: AriesAgentControllerBase = Depends(yoma_agent)
):

    return await aries_controller.multitenant.get_subwallet_authtoken_by_id(wallet_id)


@router.post("/update-subwallet")
async def update_subwallet(
    payload: dict,
    wallet_id: str,
    aries_controller: AriesAgentControllerBase = Depends(yoma_agent),
):

    # Should we return "Success" and nothing else?
    return await aries_controller.multitenant.update_subwallet_by_id(payload, wallet_id)


@router.get("/get-wallet-by-id")
async def get_subwallet(
    wallet_id: str,
    aries_controller: AriesAgentControllerBase = Depends(yoma_agent),
):

    return await aries_controller.multitenant.get_single_subwallet_by_id(wallet_id)

    # except Exception as e:
    #     err_trace = traceback.print_exc()
    #     logger.error(
    #         f"Failed to get subwallet. The following error occured:\n{e!r}\n{err_trace}"
    #     )
    #     raise e


@router.get("query-subwallet")
async def query_subwallet(
    wallet_name: str,
    aries_controller: AriesAgentControllerBase = Depends(yoma_agent),
):

    return await aries_controller.multitenant.query_subwallets(wallet_name)

    # except Exception as e:
    #     err_trace = traceback.print_exc()
    #     logger.error(
    #         f"Failed to get subwallet. The following error occured:\n{e!r}\n{err_trace}"
    #     )
    #     raise e
