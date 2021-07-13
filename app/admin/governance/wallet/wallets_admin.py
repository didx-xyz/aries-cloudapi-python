import logging

from fastapi import APIRouter, Depends
from aries_cloudcontroller import AriesAgentControllerBase

from dependencies import *

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/wallet-admin", tags=["wallets"])


@router.get("/create-local-did")
async def create_local_did(
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    """
    Create Local DID
    """

    return await aries_controller.wallet.create_did()


@router.get("/list-dids")
async def list_dids(
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):

    return await aries_controller.wallet.get_dids()


@router.get("/fetch-current-did")
async def fetch_current_did(
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    """
    Fetch the current public DID
    """
    return await aries_controller.wallet.get_public_did()


@router.patch("/rotate-keypair")
async def rotate_keypair(
    did: str,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):

    return await aries_controller.wallet.rotate_pub_key_pair(did)


@router.get("/get-did-endpoint/{did}")
async def get_did_endpoint(
    did: str,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):

    return await aries_controller.wallet.get_did_endpoint(did)


@router.post("/assign-pub-did")
async def assign_pub_did(
    did: str,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    """
    Assign the current public DID
    """
    return await aries_controller.wallet.assign_public_did(did)


@router.post("/set-did-endpoint")
async def set_did_endpoint(
    did: str,
    endpoint,
    endpoint_type,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    """
    Update Endpoint in wallet and on ledger if posted to it
    """
    return await aries_controller.wallet.set_did_endpoint(did, endpoint, endpoint_type)
