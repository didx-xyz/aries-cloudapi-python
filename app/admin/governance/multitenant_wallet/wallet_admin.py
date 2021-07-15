import logging

from fastapi import APIRouter, Depends


from aries_cloudcontroller import AriesAgentControllerBase


from dependencies import admin_agent_selector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/wallet-multitenant", tags=["Admin: wallets"])


# TODO: This should be somehow restricted?!
@router.post("/create-wallet")
async def create_wallet(
    wallet_payload: dict = None,
    aries_controller: AriesAgentControllerBase = Depends(admin_agent_selector),
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
    aries_controller: AriesAgentControllerBase = Depends(admin_agent_selector),
):

    response = await aries_controller.multitenant.remove_subwallet_by_id(wallet_id)
    if response == {}:
        return "Successfully removed wallet"
    else:
        return "Unable to delete subwallet"


@router.get("/{wallet_id}/auth-token")
async def get_subwallet_auth_token(
    wallet_id: str,
    aries_controller: AriesAgentControllerBase = Depends(admin_agent_selector),
):
    return await aries_controller.multitenant.get_subwallet_authtoken_by_id(
        wallet_id=wallet_id
    )


@router.post("/{wallet_id}")
async def update_subwallet(
    payload: dict,
    wallet_id: str,
    aries_controller: AriesAgentControllerBase = Depends(admin_agent_selector),
):
    return await aries_controller.multitenant.update_subwallet_by_id(payload, wallet_id)


@router.get("/query-subwallet")
async def query_subwallet(
    wallet_name: str = None,
    aries_controller: AriesAgentControllerBase = Depends(admin_agent_selector),
):
    return await aries_controller.multitenant.query_subwallets(wallet_name=wallet_name)


@router.get("/{wallet_id}")
async def get_subwallet(
    wallet_id: str,
    aries_controller: AriesAgentControllerBase = Depends(admin_agent_selector),
):
    return await aries_controller.multitenant.get_single_subwallet_by_id(wallet_id)
