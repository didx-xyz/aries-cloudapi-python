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
from app.dependencies.auth import AcaPyAuth, acapy_auth_from_header
from app.exceptions import handle_acapy_call
from shared.log_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/wallet/credentials", tags=["wallet"])


@router.get(
    "",
    response_model=CredInfoList,
    summary="Fetch a list of credentials from the wallet",
)
async def list_credentials(
    count: Optional[str] = None,
    start: Optional[str] = None,
    wql: Optional[str] = None,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> CredInfoList:
    """
    Fetch a list of credentials from the wallet.
    ---

    The WQL or wallet query language parameter can be used to filter credentials returned from the wallet.
    The WQL query is a string that can be used to filter records based on the attributes name and value of the record.

    The following string will look for the credential with the attribute `age` with value `21`:

        {"attr::age::value": "21"}

    See more on WQL queries [here](https://hyperledger-indy.readthedocs.io/projects/sdk/en/latest/docs/design/011-wallet-query-language/README.html).

    Parameters:
    ---
        count: Optional[str]
            The number of records to return.
        start: Optional[str]
            The number of records to skip before starting to return records.
        wql: Optional[str]
            A WQL query to filter records.

    Returns:
    ---
        CredInfoList
            A list of credential records.

    """
    logger.debug("GET request received: List credentials")

    async with client_from_auth(auth) as aries_controller:
        logger.debug("Fetching credentials")
        results = await handle_acapy_call(
            logger=logger,
            acapy_call=aries_controller.credentials.get_records,
            count=count,
            start=start,
            wql=wql,
        )

    logger.debug("Successfully listed credentials.")
    return results


@router.get(
    "/{referent}", response_model=IndyCredInfo, summary="Fetch a credential by ID"
)
async def get_credential_record(
    referent: str,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> IndyCredInfo:
    """
    Fetch a specific credential by referent.
    ---

    The referent is the ID of the credential to fetch.

    Parameters:
    ---
        referent: str
            The ID of the credential to fetch.

    Returns:
    ---
        IndyCredInfo
            The credential record.
    """
    bound_logger = logger.bind(credential_id=credential_id)
    bound_logger.debug("GET request received: Fetch specific credential by ID")

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Fetching credential")
        result = await handle_acapy_call(
            logger=bound_logger,
            acapy_call=aries_controller.credentials.get_record,
            credential_id=referent,
        )

    bound_logger.debug("Successfully fetched credential.")
    return result


@router.delete("/{referent}", status_code=204, summary="Delete a credential by ID")
async def delete_credential(
    referent: str,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> None:
    """
    Remove a specific credential from the wallet by ID.
    ---

    The referent is the ID of the credential to delete.

    Parameters:
    ---
        referent: str
            The ID of the credential to delete.

    Returns:
    ---
        status_code: 204

    """
    bound_logger = logger.bind(referent=referent)
    bound_logger.debug("DELETE request received: Remove specific credential by ID")

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Deleting credential")
        await handle_acapy_call(
            logger=bound_logger,
            acapy_call=aries_controller.credentials.delete_record,
            credential_id=referent,
        )

    bound_logger.debug("Successfully deleted credential.")


@router.get(
    "/{referent}/mime-types",
    response_model=AttributeMimeTypesResult,
    summary="Retrieve attribute MIME types of a credential",
)
async def get_credential_mime_types(
    referent: str,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> AttributeMimeTypesResult:
    """
    Retrieve attribute MIME types of a specific credential by ID.
    ---

    Parameters:
    ---
        referent: str
            The ID of the credential to fetch attribute MIME types for.

    Returns:
    ---
        AttributeMimeTypesResult
            The attribute MIME types of the credential.

    """
    bound_logger = logger.bind(referent=referent)
    bound_logger.debug(
        "GET request received: Retrieve attribute MIME types for a specific credential"
    )

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Fetching MIME types")
        result = await handle_acapy_call(
            logger=bound_logger,
            acapy_call=aries_controller.credentials.get_credential_mime_types,
            credential_id=referent,
        )

    bound_logger.debug("Successfully fetched attribute MIME types.")
    return result


@router.get(
    "/{referent}/revocation-status",
    response_model=CredRevokedResult,
    summary="Get revocation status of a credential",
)
async def get_credential_revocation_status(
    referent: str,
    from_: Optional[str] = None,
    to: Optional[str] = None,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> CredRevokedResult:
    """
    Query the revocation status of a specific credential by ID.
    ---

    The status can be check on a specific time range by providing the `from_` and `to` parameters.
    Pass the seconds, since Unix epoch, to the `from_` and `to` parameters to query the revocation status for a specific time range.

    Parameters:
    ---
        referent: str
            The ID of the credential to query revocation status for.
        from_: Optional[str]
            The timestamp to start the query from.
        to: Optional[str]
            The timestamp to end the query at.

    Returns:
    ---
        CredRevokedResult
            The revocation status of the credential.

    """
    bound_logger = logger.bind(referent=referent)
    bound_logger.debug(
        "GET request received: Query revocation status for a specific credential"
    )

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Fetching revocation status")
        result = await handle_acapy_call(
            logger=bound_logger,
            acapy_call=aries_controller.credentials.get_revocation_status,
            credential_id=referent,
            var_from=from_,
            to=to,
        )

    bound_logger.debug("Successfully fetched revocation status.")
    return result


@router.post(
    "/w3c",
    response_model=VCRecordList,
    summary="Fetch a list of W3C credentials from the wallet",
)
async def list_w3c_credentials(
    count: Optional[str] = None,
    start: Optional[str] = None,
    wql: Optional[str] = None,
    body: Optional[W3CCredentialsListRequest] = None,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> VCRecordList:
    """
    Fetch a list of W3C credentials from the wallet.
    ---

    Parameters:
    ---
        count: Optional[str]
            The number of records to return.
        start: Optional[str]
            The number of records to skip before starting to return records.
        wql: Optional[str]
            A WQL query to filter records.
        body: Optional[W3CCredentialsListRequest]  <-- TODO what is this?
            A request body to filter records.

    Returns:
    ---
        VCRecordList
            A list of W3C credential records.
    """
    logger.debug("GET request received: List W3C credentials")

    async with client_from_auth(auth) as aries_controller:
        logger.debug("Fetching W3C credentials")
        results = await handle_acapy_call(
            logger=logger,
            acapy_call=aries_controller.credentials.get_w3c_credentials,
            count=count,
            start=start,
            wql=wql,
            body=body,
        )

    logger.debug("Successfully listed W3C credentials.")
    return results


@router.get(
    "/w3c/{referent}", response_model=VCRecord, summary="Fetch a W3C credential by ID"
)
async def get_w3c_credential(
    referent: str,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> VCRecord:
    """
    Fetch a specific W3C credential by ID.
    ---

    Parameters:
    ---
        referent: str
            The ID of the W3C credential to fetch.

    Returns:
    ---
        VCRecord
            The W3C credential.

    """
    bound_logger = logger.bind(credential_id=credential_id)
    bound_logger.debug("GET request received: Fetch specific W3C credential by ID")

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Fetching W3C credential")
        result = await handle_acapy_call(
            logger=bound_logger,
            acapy_call=aries_controller.credentials.get_w3c_credential,
            credential_id=referent,
        )

    bound_logger.debug("Successfully fetched W3C credential.")
    return result


@router.delete("/w3c/{referent}", status_code=204, summary="Delete W3C credential")
async def delete_w3c_credential(
    referent: str,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> None:
    """
    Remove a specific W3C credential from the wallet by ID.
    ---

    Parameters:
    ---
        referent: str
            The ID of the W3C credential to delete.

    Returns:
    ---
        status_code: 204
    """
    bound_logger = logger.bind(credential_id=credential_id)
    bound_logger.debug("DELETE request received: Remove specific W3C credential by ID")

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Deleting W3C credential")
        await handle_acapy_call(
            logger=bound_logger,
            acapy_call=aries_controller.credentials.delete_w3c_credential,
            credential_id=referent,
        )

    bound_logger.debug("Successfully deleted W3C credential.")
