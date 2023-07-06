from typing import List

from aries_cloudcontroller import DID, DIDEndpoint, DIDEndpointWithType
from fastapi import APIRouter, Depends

from app.dependencies.acapy_clients import client_from_auth
from app.dependencies.auth import AcaPyAuth, acapy_auth
from app.exceptions.cloud_api_error import CloudApiException
from app.facades import acapy_wallet
from app.generic.wallet.models import SetDidEndpointRequest
from shared.log_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/wallet/dids", tags=["wallet"])


@router.post("", response_model=DID)
async def create_did(
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """Create Local DID."""
    logger.info("POST request received: Create DID")

    async with client_from_auth(auth) as aries_controller:
        logger.debug("Creating DID")
        result = await acapy_wallet.create_did(aries_controller)

    logger.info("Successfully created DID.")
    return result


@router.get("", response_model=List[DID])
async def list_dids(
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """
    Retrieve list of DIDs.
    """
    logger.info("GET request received: Retrieve list of DIDs")

    async with client_from_auth(auth) as aries_controller:
        logger.debug("Fetching DIDs")
        did_result = await aries_controller.wallet.get_dids()

    if not did_result.results:
        logger.info("No DIDs returned.")
        return []

    logger.info("Successfully fetched list of DIDs.")
    return did_result.results


@router.get("/public", response_model=DID)
async def get_public_did(
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """
    Fetch the current public DID.
    """
    logger.info("GET request received: Fetch public DID")

    async with client_from_auth(auth) as aries_controller:
        logger.debug("Fetching public DID")
        result = await aries_controller.wallet.get_public_did()

    if not result.result:
        logger.info("Bad request: no public DID found.")
        raise CloudApiException("No public did found.", 404)

    logger.info("Successfully fetched public DID.")
    return result.result


@router.put("/public", response_model=DID)
async def set_public_did(
    did: str,
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """Set the current public DID."""
    logger.info("PUT request received: Set public DID")

    async with client_from_auth(auth) as aries_controller:
        logger.debug("Setting public DID")
        result = await acapy_wallet.set_public_did(aries_controller, did)

    logger.info("Successfully set public DID.")
    return result


@router.patch("/{did}/rotate-keypair", status_code=204)
async def rotate_keypair(
    did: str,
    auth: AcaPyAuth = Depends(acapy_auth),
):
    bound_logger = logger.bind(body={"did": did})
    bound_logger.info("PATCH request received: Rotate keypair for DID")
    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Rotating keypair")
        await aries_controller.wallet.rotate_keypair(did=did)

    bound_logger.info("Successfully rotated keypair.")


@router.get("/{did}/endpoint", response_model=DIDEndpoint)
async def get_did_endpoint(
    did: str,
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """Get DID endpoint."""
    bound_logger = logger.bind(body={"did": did})
    bound_logger.info("GET request received: Get endpoint for DID")
    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Fetching DID endpoint")
        result = await aries_controller.wallet.get_did_endpoint(did=did)

    bound_logger.info("Successfully fetched DID endpoint.")
    return result


@router.post("/{did}/endpoint", status_code=204)
async def set_did_endpoint(
    did: str,
    body: SetDidEndpointRequest,
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """Update Endpoint in wallet and on ledger if posted to it."""

    # "Endpoint" type is for making connections using public indy DIDs
    bound_logger = logger.bind(body={"did": did, "body": body})
    bound_logger.info("POST request received: Get endpoint for DID")

    endpoint_type = "Endpoint"

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Setting DID endpoint")
        await aries_controller.wallet.set_did_endpoint(
            body=DIDEndpointWithType(
                did=did, endpoint=body.endpoint, endpoint_type=endpoint_type
            )
        )

    bound_logger.info("Successfully set DID endpoint.")
