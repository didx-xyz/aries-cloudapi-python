import logging
import traceback
from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from utils import create_pub_did, create_controller

from schemas import (
    DidCreationResponse,
    InitWalletRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wallets", tags=["wallets"])

# TODO Should the admin_api_key be a dummy variable so the controller doesn't function w/o providing it?
# This all smells really - this has to be done in a better manner


@router.get("/create-pub-did", tags=["did"], response_model=DidCreationResponse)
async def create_public_did(
    api_key: Optional[str] = Header(None),
    wallet_id: Optional[str] = Header(None),
    tenant_jwt: Optional[str] = Header(None),
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
    auth_headers = {
        "api_key": api_key,
        "wallet_id": wallet_id,
        "tenant_jwt": tenant_jwt,
    }
    try:
        return await create_pub_did(auth_headers)
    except Exception as e:
        err_trace = traceback.print_exc()
        logger.error(
            f"Failed to create public DID. The following error occured:\n{e!r}\n{err_trace}"
        )
        raise e


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
    wallet_payload: InitWalletRequest,
    api_key: Optional[str] = Header(None),
    wallet_id: Optional[str] = Header(None),
    tenant_jwt: Optional[str] = Header(None),
):
    """
    Create a new wallet

    Parameters:
    -----------
    wallet_payload: dict
        The payload for creating the wallet
    api_key: Header(None)
        The request header object api_key
    wallet_id: Header(None)
        The request header object wallet_id
    tenant_jwt: Header(None)
        The request header object tenant_jwt

    Returns:
    --------
    The response object from creating a wallet on the ledger
    """
    auth_headers = {
        "api_key": api_key,
        "wallet_id": wallet_id,
        "tenant_jwt": tenant_jwt,
    }
    try:
        async with create_controller(auth_headers) as controller:
            if controller.is_multitenant:
                # TODO replace with model for payload/wallet like
                # described https://fastapi.tiangolo.com/tutorial/body/
                # TODO Remove this default wallet. This has to be provided
                # At least unique values for eg label, The rest could be filled
                # with default values like image_url could point to a defautl avatar img
                if not wallet_payload:
                    payload = {
                        "image_url": "https://aries.ca/images/sample.png",
                        "key_management_mode": "managed",
                        "label": "YOMA",
                        "wallet_dispatch_type": "default",
                        "wallet_key": "MySecretKey1234",
                        "wallet_name": "YOMAsWallet",
                        "wallet_type": "indy",
                    }
                else:
                    payload = wallet_payload
                wallet_response = await controller.multitenant.create_subwallet(payload)
            else:
                # TODO: Implement wallet_response as schema if that is useful
                wallet_response = await controller.wallet.create_did()
            return wallet_response
    except Exception as e:
        logger.error(f"Failed to create wallet:\n{e!r}")
        raise HTTPException(
            status_code=500,
            detail=f"Something went wrong: {e!r}",
        )
