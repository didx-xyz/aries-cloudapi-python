import logging
from typing import List

from aries_cloudcontroller import DID, AcaPyClient, DIDEndpoint, DIDEndpointWithType
from fastapi import APIRouter, Depends

from app.dependencies import agent_selector
from app.facades import acapy_wallet
from app.generic.wallet.models import SetDidEndpointRequest
from shared import CloudApiException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wallet/dids", tags=["wallet"])


@router.post("", response_model=DID)
async def create_did(
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """Create Local DID."""

    return await acapy_wallet.create_did(aries_controller)


@router.get("", response_model=List[DID])
async def list_dids(
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Retrieve list of DIDs.
    """

    did_result = await aries_controller.wallet.get_dids()

    if not did_result.results:
        return []

    return did_result.results


@router.get("/public", response_model=DID)
async def get_public_did(
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Fetch the current public DID.
    """
    result = await aries_controller.wallet.get_public_did()

    if not result.result:
        raise CloudApiException("No public did found", 404)

    return result.result


@router.put("/public", response_model=DID)
async def set_public_did(
    did: str,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """Set the current public DID."""

    return await acapy_wallet.set_public_did(aries_controller, did)


@router.patch("/{did}/rotate-keypair", status_code=204)
async def rotate_keypair(
    did: str,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    await aries_controller.wallet.rotate_keypair(did=did)


@router.get("/{did}/endpoint", response_model=DIDEndpoint)
async def get_did_endpoint(
    did: str,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """Get DID endpoint."""
    return await aries_controller.wallet.get_did_endpoint(did=did)


@router.post("/{did}/endpoint", status_code=204)
async def set_did_endpoint(
    did: str,
    body: SetDidEndpointRequest,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """Update Endpoint in wallet and on ledger if posted to it."""

    # "Endpoint" type is for making connections using public indy DIDs
    endpoint_type = "Endpoint"

    await aries_controller.wallet.set_did_endpoint(
        body=DIDEndpointWithType(
            did=did, endpoint=body.endpoint, endpoint_type=endpoint_type
        )
    )
