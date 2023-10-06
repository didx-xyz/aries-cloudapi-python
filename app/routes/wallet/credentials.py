from typing import Optional

from aries_cloudcontroller import (
    AttributeMimeTypesResult,
    CredInfoList,
    CredRevokedResult,
    IndyCredInfo,
    VCRecord,
    VCRecordList,
    W3CCredentialsListRequest,
)
from fastapi import APIRouter, Depends

from app.dependencies.acapy_clients import client_from_auth
from app.dependencies.auth import AcaPyAuth, acapy_auth
from shared.log_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/wallet/credentials", tags=["wallet"])


@router.get("", response_model=CredInfoList)
async def list_credentials(
    count: Optional[str] = None,
    start: Optional[str] = None,
    wql: Optional[str] = None,
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """Fetch a list of credentials from the wallet."""
    logger.info("GET request received: List credentials")

    async with client_from_auth(auth) as aries_controller:
        logger.debug("Fetching credentials")
        results = await aries_controller.credentials.get_records(
            count=count, start=start, wql=wql
        )

    logger.info("Successfully listed credentials.")
    return results


@router.get("/{credential_id}", response_model=IndyCredInfo)
async def get_credential_record(
    credential_id: str,
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """Fetch a specific credential by ID."""
    bound_logger = logger.bind(credential_id=credential_id)
    bound_logger.info("GET request received: Fetch specific credential by ID")

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Fetching credential")
        result = await aries_controller.credentials.get_record(
            credential_id=credential_id
        )

    bound_logger.info("Successfully fetched credential.")
    return result


@router.delete("/{credential_id}", status_code=204)
async def delete_credential(
    credential_id: str,
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """Remove a specific credential from the wallet by ID."""
    bound_logger = logger.bind(credential_id=credential_id)
    bound_logger.info("DELETE request received: Remove specific credential by ID")

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Deleting credential")
        result = await aries_controller.credentials.delete_record(
            credential_id=credential_id
        )

    bound_logger.info("Successfully deleted credential.")
    return result


@router.get("/{credential_id}/mime-types", response_model=AttributeMimeTypesResult)
async def get_credential_mime_types(
    credential_id: str,
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """Retrieve attribute MIME types of a specific credential by ID."""
    bound_logger = logger.bind(credential_id=credential_id)
    bound_logger.info(
        "GET request received: Retrieve attribute MIME types for a specific credential"
    )

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Fetching MIME types")
        result = await aries_controller.credentials.get_credential_mime_types(
            credential_id=credential_id
        )

    bound_logger.info("Successfully fetched attribute MIME types.")
    return result


@router.get("/{credential_id}/revocation-status", response_model=CredRevokedResult)
async def get_credential_revocation_status(
    credential_id: str,
    from_: Optional[str] = None,
    to: Optional[str] = None,
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """Query the revocation status of a specific credential by ID."""
    bound_logger = logger.bind(credential_id=credential_id)
    bound_logger.info(
        "GET request received: Query revocation status for a specific credential"
    )

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Fetching revocation status")
        result = await aries_controller.credentials.get_revocation_status(
            credential_id=credential_id, from_=from_, to=to
        )

    bound_logger.info("Successfully fetched revocation status.")
    return result


@router.get("/w3c", response_model=VCRecordList)
async def list_w3c_credentials(
    count: Optional[str] = None,
    start: Optional[str] = None,
    wql: Optional[str] = None,
    body: Optional[W3CCredentialsListRequest] = None,
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """Fetch a list of W3C credentials from the wallet."""
    logger.info("GET request received: List W3C credentials")

    async with client_from_auth(auth) as aries_controller:
        logger.debug("Fetching W3C credentials")
        results = await aries_controller.credentials.get_w3c_credentials(
            count=count, start=start, wql=wql, body=body
        )

    logger.info("Successfully listed W3C credentials.")
    return results


@router.get("/w3c/{credential_id}", response_model=VCRecord)
async def get_w3c_credential(
    credential_id: str,
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """Fetch a specific W3C credential by ID."""
    bound_logger = logger.bind(credential_id=credential_id)
    bound_logger.info("GET request received: Fetch specific W3C credential by ID")

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Fetching W3C credential")
        result = await aries_controller.credentials.get_w3c_credential(
            credential_id=credential_id
        )

    bound_logger.info("Successfully fetched W3C credential.")
    return result


@router.delete("/w3c/{credential_id}", status_code=204)
async def delete_w3c_credential(
    credential_id: str,
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """Remove a specific W3C credential from the wallet by ID."""
    bound_logger = logger.bind(credential_id=credential_id)
    bound_logger.info("DELETE request received: Remove specific W3C credential by ID")

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Deleting W3C credential")
        result = await aries_controller.credentials.delete_w3c_credential(
            credential_id=credential_id
        )

    bound_logger.info("Successfully deleted W3C credential.")
    return result
