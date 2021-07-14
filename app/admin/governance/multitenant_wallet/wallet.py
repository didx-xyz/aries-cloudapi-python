from typing import Optional

import logging
from pydantic import BaseModel

from acapy_ledger_facade import create_pub_did
from aries_cloudcontroller import AriesAgentControllerBase
from dependencies import member_admin_agent, yoma_agent, admin_agent_selector
from fastapi import APIRouter, Depends
from schemas import DidCreationResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/wallets", tags=["Admin: Wallets"])


@router.get("/create-pub-did", response_model=DidCreationResponse)
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


class CreateWalletRequest(BaseModel):
    image_url: Optional[str]
    label: str
    wallet_key: str
    wallet_name: str

    key_management_mode: str = "managed"
    wallet_dispatch_type: str = "default"
    wallet_type: str = "indy"


# TODO: This should be somehow restricted?!
@router.post("/create-wallet")
async def create_wallet(
    wallet_payload: CreateWalletRequest,
    aries_controller: AriesAgentControllerBase = Depends(admin_agent_selector),
):
    """
    Create a new wallet

    Parameters:
    -----------
    wallet_payload: CreateWalletRequest
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
    # set wallet statics:
    if wallet_payload:
        wallet_response = await aries_controller.multitenant.create_subwallet(
            wallet_payload.dict()
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
