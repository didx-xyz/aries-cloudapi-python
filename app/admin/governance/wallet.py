import logging, json

from fastapi import APIRouter, HTTPException, Depends

from schemas import (
    DidCreationResponse,
    InitWalletRequest,
)
from aries_cloudcontroller import AriesAgentControllerBase
import traceback

from acapy_ledger_facade import create_pub_did
from dependencies import *

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wallets", tags=["wallets"])

# TODO Should the admin_api_key be a dummy variable so the controller doesn't function w/o providing it?
# This all smells really - this has to be done in a better manner


@router.get("/create-pub-did", tags=["did"], response_model=DidCreationResponse)
async def create_public_did(
    aries_controller: AriesAgentControllerBase,
):
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
    return await create_pub_did(aries_controller)


# TODO: This should be somehow retsricted?!
@router.post("/create-wallet")
async def create_wallet(
    wallet_payload: dict = None,
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
    # wallet_payload= json.dumps(wallet_payload)

    # wallet_response = await aries_controller.multitenant.create_subwallet(wallet_payload)

    return print(type(wallet_payload))
    # else:
    #     # TODO: Implement wallet_response as schema if that is useful
    #     wallet_response = await controller.wallet.create_did()
    # return wallet_response


@router.get("/remove-wallet")
async def remove_wallet_by_id(
    wallet_id: str,
    aries_controller: AriesAgentControllerBase = Depends(member_admin_agent),
):

    response = await aries_controller.multitenant.remove_subwallet_by_id(wallet_id)
    # Should this be success or the response??
    if response == {}:
        final_respnse = "Success"
    else:
        final_respnse = "Unable to delete subwallet"

    return final_respnse


@router.get("/get-subwallet-auth-token")
async def get_subwallet_auth_token(
    wallet_id: str,
    aries_controller: AriesAgentControllerBase = Depends(member_admin_agent),
):

    return await aries_controller.multitenant.get_subwallet_authtoken_by_id(wallet_id)


@router.post("/update-subwallet")
async def update_subwallet(
    payload: dict,
    wallet_id: str,
    aries_controller: AriesAgentControllerBase = Depends(member_admin_agent),
):

    # Should we return "Success" and nothing else?
    return await aries_controller.multitenant.update_subwallet_by_id(payload, wallet_id)


@router.get("/get-wallet-by-id")
async def get_subwallet(
    wallet_id: str,
    aries_controller: AriesAgentControllerBase = Depends(member_admin_agent),
):

    return await aries_controller.multitenant.get_single_subwallet_by_id(wallet_id)

    # except Exception as e:
    #     err_trace = traceback.print_exc()
    #     logger.error(
    #         f"Failed to get subwallet. The following error occured:\n{e!r}\n{err_trace}"
    #     )
    #     raise e


@router.get("/query-subwallet")
async def query_subwallet(
    wallet_name: str = None,
    aries_controller: AriesAgentControllerBase = Depends(member_admin_agent),
):

    return await aries_controller.multitenant.query_subwallets(wallet_name)

    # except Exception as e:
    #     err_trace = traceback.print_exc()
    #     logger.error(
    #         f"Failed to get subwallet. The following error occured:\n{e!r}\n{err_trace}"
    #     )
    #     raise e
