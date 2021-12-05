import logging

from aries_cloudcontroller import AcaPyClient, DIDEndpointWithType, DIDList, DIDCreate
from fastapi import APIRouter, Depends

from app.dependencies import agent_selector
from app.facades.acapy_ledger import accept_taa_if_required

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dids", tags=["dids"])


@router.post("/")
async def create_local_did(
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Create local did.
    """

    return await aries_controller.wallet.create_did(body=DIDCreate())


@router.get("/", response_model=DIDList)
async def get_dids(
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Get list of DIDs.
    """
    return await aries_controller.wallet.get_dids()


@router.get("/public")
async def get_public_did(
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Fetch the current public did.
    """
    return await aries_controller.wallet.get_public_did()


@router.put("/public")
async def set_public_did(
    did: str,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Assign the current public did

    Parameter:
    ----------
    did: str
    """
    await accept_taa_if_required(aries_controller)
    return await aries_controller.wallet.set_public_did(did=did)


@router.patch("/{did}/rotate-keypair")
async def rotate_keypair(
    did: str,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    return await aries_controller.wallet.rotate_keypair(did=did)


@router.get("/{did}/endpoint")
async def get_did_endpoint(
    did: str,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Get DID endpoint.
    """
    return await aries_controller.wallet.get_did_endpoint(did=did)


@router.put("/{did}/endpoint")
async def set_did_endpoint(
    did: str,
    endpoint: str,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Update Endpoint in wallet and on ledger if posted to it.

    Parameters:
    ------------
    did: str
    endpoint: str
    """
    return await aries_controller.wallet.set_did_endpoint(
        body=DIDEndpointWithType(did=did, endpoint=endpoint, endpoint_type="Endpoint")
    )
