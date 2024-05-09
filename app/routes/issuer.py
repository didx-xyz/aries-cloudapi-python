from typing import List, Optional
from uuid import UUID

from aries_cloudcontroller import IssuerCredRevRecord
from fastapi import APIRouter, Depends, Query

from app.dependencies.acapy_clients import client_from_auth
from app.dependencies.auth import AcaPyAuth, acapy_auth_from_header
from app.exceptions import CloudApiException
from app.models.issuer import (
    ClearPendingRevocationsRequest,
    ClearPendingRevocationsResult,
    CreateOffer,
    CredentialType,
    PublishRevocationsRequest,
    RevokeCredential,
    SendCredential,
)
from app.services import revocation_registry
from app.services.acapy_ledger import schema_id_from_credential_definition_id
from app.services.acapy_wallet import assert_public_did
from app.services.trust_registry.util.issuer import assert_valid_issuer
from app.util.acapy_issuer_utils import (
    IssueCredentialFacades,
    issuer_from_id,
    issuer_from_protocol_version,
)
from app.util.did import did_from_credential_definition_id, qualified_did_sov
from shared.log_config import get_logger
from shared.models.credential_exchange import (
    CredentialExchange,
    Role,
    State,
    back_to_v1_credential_state,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/issuer/credentials", tags=["issuer"])


@router.post("", summary="Submit a Credential Offer", response_model=CredentialExchange)
async def send_credential(
    credential: SendCredential,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> CredentialExchange:
    """
    Create and send a credential. Automating the entire flow.
    ---------------------------------------------------------
    Only a tenant with the issuer role can call this endpoint.
    Keep in mind that a holder still needs to accept the offer they receive,
    even tho this flow is automated.

    When creating a credential, the credential type must be one of indy or ld_proof.
    ```json
    {
        "type": "indy" or "ld_proof",
        "indy_credential_detail": {...}, <-- Required if type is indy
        "ld_credential_detail": {...}, <-- Required if type is ld_proof
        "save_exchange_record": false,
        "connection_id": "string",
        "protocol_version": "v2" <-- v1 is supported but will be deprecated
    }
    ```
    Read more at:
        https://github.com/hyperledger/aries-rfcs/blob/main/features/0453-issue-credential-v2/README.md

    Setting the 'save_exchange_record' field to True will save the exchange record after the flow completes.
    This is useful if you want to keep track of the credential exchange record after the fact.

    Request Body:
    ------------
        credential: Credential
            payload for sending a credential

    Returns:
    --------
        payload: CredentialExchange
            The response object from sending a credential
        status_code: 200
    """
    bound_logger = logger.bind(
        body={
            # Do not log credential attributes:
            "connection_id": credential.connection_id,
            "protocol_version": credential.protocol_version,
            "credential_type": credential.type,
        }
    )
    bound_logger.info("POST request received: Send credential")

    issuer = issuer_from_protocol_version(credential.protocol_version)

    async with client_from_auth(auth) as aries_controller:
        # Assert the agent has a public did
        try:
            public_did = await assert_public_did(aries_controller)
        except CloudApiException as e:
            bound_logger.warning("Asserting agent has public DID failed: {}", e)
            raise CloudApiException(
                "Wallet making this request has no public DID. Only issuers with a public DID can make this request.",
                403,
            ) from e

        schema_id = None
        if credential.type == CredentialType.INDY:
            # Retrieve the schema_id based on the credential definition id
            schema_id = await schema_id_from_credential_definition_id(
                aries_controller,
                credential.indy_credential_detail.credential_definition_id,
            )

        # Make sure we are allowed to issue according to trust registry rules
        await assert_valid_issuer(public_did, schema_id)

        try:
            bound_logger.debug("Sending credential")
            result = await issuer.send_credential(
                controller=aries_controller, credential=credential
            )
        except CloudApiException as e:
            raise CloudApiException(
                f"Failed to send credential: {e.detail}", e.status_code
            ) from e

    if result:
        bound_logger.info("Successfully sent credential.")
    else:
        bound_logger.warning("No result from sending credential.")
    return result


@router.post(
    "/create-offer",
    summary="Create a Credential Offer (not bound to a connection)",
    response_model=CredentialExchange,
)
async def create_offer(
    credential: CreateOffer,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> CredentialExchange:
    """
    Create a credential offer not bound to any connection.
    ------------------------------------------------------
    The create offer endpoint is used to create a credential offer that is not bound to any connection.
    This is useful if you want to create an offer that you can send to multiple connections.

    The credential type must be one of indy or ld_proof.
    ```json
    {
        "type": "indy" or "ld_proof",
        "indy_credential_detail": {...}, <-- Required if type is indy
        "ld_credential_detail": {...}, <-- Required if type is ld_proof
        "save_exchange_record": false,
        "protocol_version": "v2" <-- v1 is supported but will be deprecated
    }
    ```
    Read more at:
        https://github.com/hyperledger/aries-rfcs/blob/main/features/0453-issue-credential-v2/README.md

    Request Body:
    ------------
        credential: Credential
            payload for sending a credential

    Returns:
    --------
        The response object from sending a credential
    """
    bound_logger = logger.bind(
        body={
            # Do not log credential attributes:
            "protocol_version": credential.protocol_version,
            "credential_type": credential.type,
        }
    )
    bound_logger.info("POST request received: Create credential offer")

    issuer = issuer_from_protocol_version(credential.protocol_version)

    async with client_from_auth(auth) as aries_controller:
        # Assert the agent has a public did
        try:
            public_did = await assert_public_did(aries_controller)
        except CloudApiException as e:
            bound_logger.warning("Asserting agent has public DID failed: {}", e)
            raise CloudApiException(
                "Wallet making this request has no public DID. Only issuers with a public DID can make this request.",
                403,
            ) from e

        schema_id = None
        if credential.type == CredentialType.INDY:
            # Retrieve the schema_id based on the credential definition id
            schema_id = await schema_id_from_credential_definition_id(
                aries_controller,
                credential.indy_credential_detail.credential_definition_id,
            )

        # Make sure we are allowed to issue according to trust registry rules
        await assert_valid_issuer(public_did, schema_id)

        bound_logger.debug("Creating offer")
        result = await issuer.create_offer(
            controller=aries_controller,
            credential=credential,
        )

    if result:
        bound_logger.info("Successfully created credential offer.")
    else:
        bound_logger.warning("No result from creating credential offer.")
    return result


@router.post(
    "/{credential_exchange_id}/request",
    summary="Accept a Credential Offer",
    response_model=CredentialExchange,
)
async def request_credential(
    credential_exchange_id: str,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> CredentialExchange:
    """
    Send a credential request.
    --------------------------
    Send a credential request to the issuer by providing the credential exchange id.

    The holder uses this endpoint to accept an offer from an issuer.
    A holder calls this endpoint with the credential exchange id from
    a credential exchange record, with a state 'offer-received'.

    Request Body:
    -----------
        credential_exchange_id: str
            the credential id
    """
    bound_logger = logger.bind(body={"credential_exchange_id": credential_exchange_id})
    bound_logger.info("POST request received: Send credential request")

    issuer = issuer_from_id(credential_exchange_id)

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Fetching records")
        record = await issuer.get_record(aries_controller, credential_exchange_id)

        schema_id = None
        if record.type == "indy":
            if not record.credential_definition_id or not record.schema_id:
                raise CloudApiException(
                    "Record has no credential definition or schema associated. "
                    "This probably means you haven't received an offer yet.",
                    412,
                )
            issuer_did = did_from_credential_definition_id(
                record.credential_definition_id
            )
            issuer_did = qualified_did_sov(issuer_did)
            schema_id = record.schema_id
        elif record.type == "ld_proof":
            issuer_did = record.did
        else:
            raise CloudApiException("Could not resolve record type")

        await assert_valid_issuer(issuer_did, schema_id)
        # Make sure the issuer is allowed to issue this credential according to trust registry rules

        bound_logger.debug("Requesting credential")
        result = await issuer.request_credential(
            controller=aries_controller, credential_exchange_id=credential_exchange_id
        )

    if result:
        bound_logger.info("Successfully sent credential request.")
    else:
        bound_logger.warning("No result from sending credential request.")
    return result


@router.post(
    "/{credential_exchange_id}/store",
    summary="Store a Received Credential In Wallet",
    response_model=CredentialExchange,
)
async def store_credential(
    credential_exchange_id: str,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> CredentialExchange:
    """
    Store a credential.
    ------------------
    Store a credential by providing the credential exchange id.
    The credential exchange id is the id of the credential exchange record, not the credential itself.

    The holder only needs to call this endpoint if the holder receives a credential out of band

    The holder can store the credential in their wallet after receiving it from the issuer.

    Parameters:
    -----------
        credential_exchange_id: str
            credential identifier

    """
    bound_logger = logger.bind(body={"credential_exchange_id": credential_exchange_id})
    bound_logger.info("POST request received: Store credential")

    issuer = issuer_from_id(credential_exchange_id)

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Storing credential")
        result = await issuer.store_credential(
            controller=aries_controller, credential_exchange_id=credential_exchange_id
        )

    if result:
        bound_logger.info("Successfully stored credential.")
    else:
        bound_logger.warning("No result from storing credential.")
    return result


@router.get(
    "",
    summary="Fetch Credential Exchange Records",
    response_model=List[CredentialExchange],
)
async def get_credentials(
    connection_id: Optional[str] = Query(None),
    role: Optional[Role] = Query(None),
    state: Optional[State] = Query(None),
    thread_id: Optional[UUID] = Query(None),
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> List[CredentialExchange]:
    """
    Get a list of credential exchange records.
    ------------------------------------------

    These records contain information about the credentials issued to/by the tenant,
    each record in the list is related to a single credential exchange flow.

    It's important to remember that the 'credential_id' field in a record refers to
    the ID of the credential exchange record, not the credential itself.

    The thread_id is the only field that can relate a record of the issuer to a
    record of the holder or visa versa.

    An exchange record will be deleted after a flow completes if the 'save_exchange_record'
    field, in the send credential endpoint,
    is set to False (The default value).

    These records can be filtered by connection_id, role, state and thread_id.

    Parameters:
    ------------
        connection_id: str (Optional)
        role: Role (Optional): "issuer", "holder"
        state: State (Optional): "proposal-sent", "proposal-received", "offer-sent", "offer-received",
                                 "request-sent", "request-received", "credential-issued", "credential-received",
                                 "credential-revoked","abandoned", "done"
        thread_id: UUID (Optional)

    Returns:
    --------
        payload: List[CredentialExchange]
            A list of credential exchange records
    """
    bound_logger = logger.bind(body={"connection_id": connection_id})
    bound_logger.info("GET request received: Get credentials")

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Fetching v1 records")
        v1_records = await IssueCredentialFacades.v1.value.get_records(
            controller=aries_controller,
            connection_id=connection_id,
            role=role,
            state=back_to_v1_credential_state(state) if state else None,
            thread_id=str(thread_id) if thread_id else None,
        )

        bound_logger.debug("Fetching v2 records")
        v2_records = await IssueCredentialFacades.v2.value.get_records(
            controller=aries_controller,
            connection_id=connection_id,
            role=role,
            state=state,
            thread_id=str(thread_id) if thread_id else None,
        )

    result = v1_records + v2_records
    if result:
        bound_logger.info("Successfully fetched v1 and v2 records.")
    else:
        bound_logger.info("No v1 or v2 records returned.")
    return result


@router.get(
    "/{credential_exchange_id}",
    summary="Fetch a single Credential Exchange Record",
    response_model=CredentialExchange,
)
async def get_credential(
    credential_exchange_id: str,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> CredentialExchange:
    """
    Get a credential exchange record by credential id.
    -------------------------------------------------

    The record contains information about the credential issued to/by the tenant.
    The credential exchange record is related to a single credential exchange flow.

    It's important to remember the 'credential_id' is not the ID of the credential itself,
    but the id of the credential exchange record.

    An exchange record will be deleted after a flow completes if the 'save_exchange_record'
    field, in the send credential endpoint, is set to False (The default value).

    Parameters:
    -----------
        credential_exchange_id: str
            credential identifier

    Returns:
    --------
        payload: CredentialExchange
            The credential exchange record
    """
    bound_logger = logger.bind(body={"credential_exchange_id": credential_exchange_id})
    bound_logger.info("GET request received: Get credentials by credential id")

    issuer = issuer_from_id(credential_exchange_id)

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Getting credential record")
        result = await issuer.get_record(
            controller=aries_controller, credential_exchange_id=credential_exchange_id
        )

    if result:
        bound_logger.info("Successfully fetched credential.")
    else:
        bound_logger.info("No credential returned.")
    return result


@router.delete(
    "/{credential_exchange_id}", summary="Delete an Exchange Record", status_code=204
)
async def remove_credential_exchange_record(
    credential_exchange_id: str,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> None:
    """
    Remove a credential exchange record.
    ------------------------------------
    This will remove the credential exchange record associated with the provided credential exchange id.

    Parameters:
    -----------
        credential_exchange_id: str
            credential exchange record identifier

    Returns:
    --------
        payload: None
        status_code: 204
    """
    bound_logger = logger.bind(body={"credential_exchange_id": credential_exchange_id})
    bound_logger.info(
        "DELETE request received: Remove credential exchange record by id"
    )

    issuer = issuer_from_id(credential_exchange_id)

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Deleting credential")
        await issuer.delete_credential_exchange_record(
            controller=aries_controller, credential_exchange_id=credential_exchange_id
        )

    bound_logger.info("Successfully deleted credential exchange record.")


@router.post("/revoke", summary="Revoke a Credential (if revocable)", status_code=204)
async def revoke_credential(
    body: RevokeCredential,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> None:
    """
    Revoke a credential.
    --------------------
    Revoke a credential by providing the credential exchange id and the credential definition id.

    If an issuer is going to revoke more than one credential, it is recommended to set the
    'auto_publish_on_ledger' field to False, and then batch publish the revocations using
    the 'publish-revocations' endpoint.

    By batching the revocations, the issuer can save on transaction fees related to
    publishing revocations to the ledger.

    Request Body:
    -----------
        credential_exchange_id: str
            The credential exchange id

    Returns:
    --------
        payload: None
        status_code: 204
    """
    bound_logger = logger.bind(body=body)
    bound_logger.info("POST request received: Revoke credential")

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Revoking credential")
        await revocation_registry.revoke_credential(
            controller=aries_controller,
            credential_exchange_id=body.credential_exchange_id,
            credential_definition_id=body.credential_definition_id,
            auto_publish_to_ledger=body.auto_publish_on_ledger,
        )

    bound_logger.info("Successfully revoked credential.")


@router.get(
    "/revocation/record",
    summary="Fetch a Revocation Record",
    response_model=IssuerCredRevRecord,
)
async def get_credential_revocation_record(
    credential_exchange_id: Optional[str] = None,
    credential_revocation_id: Optional[str] = None,
    revocation_registry_id: Optional[str] = None,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> IssuerCredRevRecord:
    """
    Get a credential revocation record.
    -----------------------------------
    Fetch a credential revocation record by providing the credential exchange id.
    If the credential exchange id is not provided, the credential revocation id and
    revocation registry id must be provided.

    The record is the payload of the event 'issuer_cred_rev' and contains information about the
    credential's revocation status.

    The revocation registry id (rev_reg_id) and credential revocation id (cred_rev_id) can be found
    in this record if you have the credential exchange id.

    Parameters:
    -----------
        credential_exchange_id: str
            The credential exchange id
        credential_revocation_id: str
            The credential revocation id
        revocation_registry_id: str
            The revocation registry id

    Returns:
    --------
        payload: IssuerCredRevRecord
            The credential revocation record

    Raises:
    -------
        CloudApiException: 400
            If credential_exchange_id is not provided BOTH the credential_revocation_id
            and revocation_registry_id MUST be provided.
    """
    bound_logger = logger.bind(
        body={
            "credential_exchange_id": credential_exchange_id,
            "credential_revocation_id": credential_revocation_id,
            "revocation_registry_id": revocation_registry_id,
        }
    )
    bound_logger.info("GET request received: Get credential revocation record by id")

    if credential_exchange_id is None and (
        credential_revocation_id is None or revocation_registry_id is None
    ):
        raise CloudApiException(
            "If credential_exchange_id is not provided BOTH the credential_revocation_id and \
                  revocation_registry_id MUST be provided.",
            400,
        )

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Getting credential revocation record")
        revocation_record = await revocation_registry.get_credential_revocation_record(
            controller=aries_controller,
            credential_exchange_id=credential_exchange_id,
            credential_revocation_id=credential_revocation_id,
            revocation_registry_id=revocation_registry_id,
        )

    if revocation_record:
        bound_logger.info("Successfully fetched credential revocation record.")
    else:
        bound_logger.info("No credential revocation record returned.")
    return revocation_record


@router.post(
    "/publish-revocations", summary="Publish Pending Revocations", status_code=204
)
async def publish_revocations(
    publish_request: PublishRevocationsRequest,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> None:
    """
    Write batch of pending revocations to ledger.
    ---------------------------------------------
    If no revocation registry id is provided, all pending revocations
    will be published.

    If no credential revocation id is provided, all pending revocations
    for the given revocation registry id will be published.

    Where to find the revocation registry id and credential revocation id:
    When issuing a credential, against a credential definition that supports revocation,
    the issuer will receive a event on the topic 'issuer_cred_rev'. This event will contain
    the credential exchange id (cred_ex_id), the credential revocation id (cred_rev_id) and
    the revocation registry id (rev_reg_id).


    Request Body:
    -----------
        publish_request: PublishRevocationsRequest
            An instance of `PublishRevocationsRequest` containing a `revocation_registry_credential_map`. This map
            is a dictionary where each key is a revocation registry ID and its value is a list of credential
            revocation IDs to be published. Providing an empty list for a registry ID instructs the system to
            publish all pending revocations for that ID. An empty dictionary signifies that all pending
            revocations across all registry IDs should be published.

    Returns:
    --------
        payload: None
        status_code: 204
    """
    bound_logger = logger.bind(body=publish_request)
    bound_logger.info("POST request received: Publish revocations")

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Publishing revocations")
        await revocation_registry.publish_pending_revocations(
            controller=aries_controller,
            revocation_registry_credential_map=publish_request.revocation_registry_credential_map,
        )

    bound_logger.info("Successfully published revocations.")


@router.post(
    "/clear-pending-revocations",
    summary="Clear Pending Revocations",
    response_model=ClearPendingRevocationsResult,
)
async def clear_pending_revocations(
    clear_pending_request: ClearPendingRevocationsRequest,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> ClearPendingRevocationsResult:
    """
    Clear pending revocations.
    --------------------------
    If no revocation registry id is provided, all pending revocations
    will be cleared.

    If no credential revocation id is provided, all pending revocations
    for the given revocation registry id will be cleared.

    Where to find the revocation registry id and credential revocation id:
    When issuing a credential, against a credential definition that supports revocation,
    the issuer will receive a event on the topic 'issuer_cred_rev'. This event will contain
    the credential exchange id (cred_ex_id), the credential revocation id (cred_rev_id) and
    the revocation registry id (rev_reg_id).

    Request Body:
    -----------
        clear_pending_request: ClearPendingRevocationsRequest
            An instance of `ClearPendingRevocationsRequest` containing a `revocation_registry_credential_map`. This map
            is a dictionary where each key is a revocation registry ID and its value is a list of credential
            revocation IDs to be cleared. Providing an empty list for a registry ID instructs the system to
            clear all pending revocations for that ID. An empty dictionary signifies that all pending
            revocations across all registry IDs should be cleared.

    Returns:
    --------
        payload: ClearPendingRevocationsResult
            The revocations that are still pending after the clear request is performed
    """
    bound_logger = logger.bind(body=clear_pending_request)
    bound_logger.info("POST request received: Clear pending revocations")

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Clearing pending revocations")
        response = await revocation_registry.clear_pending_revocations(
            controller=aries_controller,
            revocation_registry_credential_map=clear_pending_request.revocation_registry_credential_map,
        )

    bound_logger.info("Successfully cleared pending revocations.")
    return response
