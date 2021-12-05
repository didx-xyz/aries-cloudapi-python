import logging
from typing import Optional

from aiohttp import ClientError
from aries_cloudcontroller import (
    AcaPyClient,
    CreateWalletRequest,
    CreateWalletResponse,
    CreateWalletTokenResponse,
    UpdateWalletRequest,
    WalletList,
    WalletRecord,
)
from aries_cloudcontroller.model.create_wallet_token_request import (
    CreateWalletTokenRequest,
)
from aries_cloudcontroller.model.remove_wallet_request import RemoveWalletRequest
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import Role, admin_agent_selector, agent_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/wallet-multitenant", tags=["admin: wallet"])

member_admin = agent_role(Role.MEMBER_ADMIN)


# TODO: This should be somehow restricted?!
@router.post("/create-wallet", response_model=CreateWalletResponse)
async def create_subwallet(
    wallet_payload: CreateWalletRequest,
    aries_controller: AcaPyClient = Depends(admin_agent_selector),
) -> CreateWalletResponse:
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
    wallet_response = await aries_controller.multitenancy.create_wallet(
        body=wallet_payload
    )

    return wallet_response


@router.delete("/{wallet_id}")
async def remove_subwallet_by_id(
    wallet_id: str,
    aries_controller: AcaPyClient = Depends(admin_agent_selector),
):
    """
    Remove subwallet by id.

    Parameters:
    wallet_id: str
    """
    try:
        response = await aries_controller.multitenancy.delete_wallet(
            wallet_id=wallet_id, body=RemoveWalletRequest()
        )
        if response == {}:
            return {"status": "Successfully removed wallet"}
        else:
            raise HTTPException(500, "Unable to delete sub wallet")
    except ClientError as client_error:
        if client_error.status == 401:
            return HTTPException(401, "subwallet to delete is not found")


@router.get("/{wallet_id}/auth-token", response_model=CreateWalletTokenResponse)
async def get_subwallet_auth_token(
    wallet_id: str,
    aries_controller: AcaPyClient = Depends(admin_agent_selector),
):
    return await aries_controller.multitenancy.get_auth_token(
        wallet_id=wallet_id, body=CreateWalletTokenRequest()
    )


@router.post("/{wallet_id}", response_model=WalletRecord)
async def update_subwallet(
    payload: UpdateWalletRequest,
    wallet_id: str,
    aries_controller: AcaPyClient = Depends(member_admin),
) -> WalletRecord:
    """
    Update subwallet by id.

    Parameters:
    -----------
    payload: UpdateWalletRequest
      payload for updating a subwallet
    wallet_id: str

    Returns:
    ---------
    The response object from updating a subwallet.
    """
    return await aries_controller.multitenancy.update_wallet(
        body=payload,
        wallet_id=wallet_id,
    )


@router.get("/query-subwallet", response_model=WalletList)
async def query_subwallet(
    wallet_name: Optional[str] = None,
    aries_controller: AcaPyClient = Depends(member_admin),
) -> WalletList:

    """
    Query subwallets.

    Parameters:
    -----------
    wallet_name: str (Optional)

    """
    return await aries_controller.multitenancy.get_wallets(wallet_name=wallet_name)


@router.get("/{wallet_id}", response_model=WalletRecord)
async def get_subwallet(
    wallet_id: str,
    aries_controller: AcaPyClient = Depends(member_admin),
) -> WalletRecord:
    """
    Retrieve subwallet by id.

    Parameters:
    -------------
    wallet_id: str
    """
    return await aries_controller.multitenancy.get_wallet(wallet_id=wallet_id)
