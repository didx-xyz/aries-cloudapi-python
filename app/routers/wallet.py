from typing import Optional

from fastapi import APIRouter, HTTPException, Header
import requests
import json
import os
import logging

from core import wallet
from facade import create_controller
from schemas import LedgerRequest, DidCreationResponse, InitWalletRequest

import aries_cloudcontroller


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wallets", tags=["wallets"])

admin_url = os.getenv("ACAPY_ADMIN_URL")
admin_port = os.getenv("ACAPY_ADMIN_PORT")
admin_api_key = os.getenv("ACAPY_ADMIN_API_KEY")
is_multitenant = os.getenv("IS_MULTITENANT", False)
ledger_url = os.getenv("LEDGER_NETWORK_URL")


@router.get(
    "/create-pub-did", tags=["did"], response_model=DidCreationResponse
)
async def create_public_did(req_header: Optional[str] = Header(None)): # pragma: no cover
    return wallet.create_public_did(req_header)


@router.get("/")
async def wallets_root(): # pragma: no cover
    """
    The default endpoints for wallets

    TODO: Determine what this should return or
    whether this should return anything at all
    """
    return {
        "message": "Wallets endpoint. Please, visit /docs to consult the Swagger docs."
    }


# TODO: This should be somehow retsricted?!
@router.post("/create-wallet")
async def create_wallet( # pragma: no cover
    wallet_payload: InitWalletRequest, req_header: Optional[str] = Header(None)
):
    """
    Create a new wallet

    Parameters:
    -----------
    wallet_payload: dict
        The payload for creating the wallet
    req_header: Header
        The request header object with (tenant_jwt, wallet_id) or api_key

    Returns:
    --------
    The response object from creating a wallet on the ledger
    """
    try:
        async with create_controller(req_header) as controller:
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
