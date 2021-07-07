import logging, json

from fastapi import APIRouter, HTTPException, Depends, Request

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


@router.get("/create-pub-did", tags=["did"], response_model=DidCreationResponse)
async def create_public_did(
    aries_controller: AriesAgentControllerBase = Depends(yoma_agent),
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


# TODO: This should be somehow restricted?!
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
            "wallet_type": "indy"
        }
    """
    if wallet_payload:
        wallet_response = await aries_controller.multitenant.create_subwallet(
            wallet_payload
        )
    return wallet_response


@router.delete("/{wallet_id}")
async def remove_wallet_by_id(
    wallet_id: str,
    aries_controller: AriesAgentControllerBase = Depends(member_admin_agent),
):

    response = await aries_controller.multitenant.remove_subwallet_by_id(wallet_id)
    if response == {}:
        return "Successfully removed wallet"
    else:
        return "Unable to delete subwallet"


@router.get("/{wallet_id}/auth-token")
async def get_subwallet_auth_token(
    wallet_id: str,
    aries_controller: AriesAgentControllerBase = Depends(member_admin_agent),
):
    return await aries_controller.multitenant.get_subwallet_authtoken_by_id(
        wallet_id=wallet_id
    )


@router.post("/{wallet_id}")
async def update_subwallet(
    payload: dict,
    wallet_id: str,
    aries_controller: AriesAgentControllerBase = Depends(member_admin_agent),
):
    return await aries_controller.multitenant.update_subwallet_by_id(payload, wallet_id)


@router.get("/query-subwallet")
async def query_subwallet(
    wallet_name: str = None,
    aries_controller: AriesAgentControllerBase = Depends(member_admin_agent),
):
    return await aries_controller.multitenant.query_subwallets(wallet_name=wallet_name)


@router.get("/{wallet_id}")
async def get_subwallet(
    wallet_id: str,
    aries_controller: AriesAgentControllerBase = Depends(member_admin_agent),
):
    return await aries_controller.multitenant.get_single_subwallet_by_id(wallet_id)
