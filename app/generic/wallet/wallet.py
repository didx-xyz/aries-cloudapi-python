from typing import List

from aries_cloudcontroller import DID, DIDEndpoint, DIDEndpointWithType
from fastapi import APIRouter, Depends

from app.config.log_config import get_logger
from app.dependencies.auth import AcaPyAuth, acapy_auth, client_from_auth
from app.exceptions.cloud_api_error import CloudApiException
from app.facades import acapy_wallet
from app.generic.wallet.models import SetDidEndpointRequest

logger = get_logger(__name__)

router = APIRouter(prefix="/wallet/dids", tags=["wallet"])


@router.post("", response_model=DID)
async def create_did(
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """Create Local DID."""

    async with client_from_auth(auth) as aries_controller:
        result = await acapy_wallet.create_did(aries_controller)

    return result


@router.get("", response_model=List[DID])
async def list_dids(
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """
    Retrieve list of DIDs.
    """

    async with client_from_auth(auth) as aries_controller:
        did_result = await aries_controller.wallet.get_dids()

    if not did_result.results:
        return []

    return did_result.results


@router.get("/public", response_model=DID)
async def get_public_did(
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """
    Fetch the current public DID.
    """
    async with client_from_auth(auth) as aries_controller:
        result = await aries_controller.wallet.get_public_did()

    if not result.result:
        raise CloudApiException("No public did found", 404)

    return result.result


@router.put("/public", response_model=DID)
async def set_public_did(
    did: str,
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """Set the current public DID."""

    async with client_from_auth(auth) as aries_controller:
        result = await acapy_wallet.set_public_did(aries_controller, did)

    return result


@router.patch("/{did}/rotate-keypair", status_code=204)
async def rotate_keypair(
    did: str,
    auth: AcaPyAuth = Depends(acapy_auth),
):
    async with client_from_auth(auth) as aries_controller:
        await aries_controller.wallet.rotate_keypair(did=did)


@router.get("/{did}/endpoint", response_model=DIDEndpoint)
async def get_did_endpoint(
    did: str,
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """Get DID endpoint."""
    async with client_from_auth(auth) as aries_controller:
        result = await aries_controller.wallet.get_did_endpoint(did=did)

    return result


@router.post("/{did}/endpoint", status_code=204)
async def set_did_endpoint(
    did: str,
    body: SetDidEndpointRequest,
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """Update Endpoint in wallet and on ledger if posted to it."""

    # "Endpoint" type is for making connections using public indy DIDs
    endpoint_type = "Endpoint"

    async with client_from_auth(auth) as aries_controller:
        await aries_controller.wallet.set_did_endpoint(
            body=DIDEndpointWithType(
                did=did, endpoint=body.endpoint, endpoint_type=endpoint_type
            )
        )
