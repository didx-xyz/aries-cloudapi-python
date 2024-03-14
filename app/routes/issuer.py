from typing import List, Optional
from uuid import UUID

from aries_cloudcontroller import ApiException, IssuerCredRevRecord
from fastapi import APIRouter, Depends, Query

from app.dependencies.acapy_clients import client_from_auth
from app.dependencies.auth import AcaPyAuth, acapy_auth
from app.exceptions import CloudApiException
from app.models.issuer import (
    ClearPendingRevocationsRequest,
    ClearPendingRevocationsResult,
    CreateOffer,
    CredentialType,
    PublishRevocationsRequest,
    RevokeCredential,
    Role,
    SendCredential,
    State,
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
    back_to_v1_credential_state,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/issuer/credentials", tags=["issuer"])


@router.get("", response_model=List[CredentialExchange])
async def get_credentials(
    connection_id: Optional[UUID] = Query(None),
    role: Optional[Role] = Query(None),
    state: Optional[State] = Query(None),
    thread_id: Optional[UUID] = Query(None),
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """
        Get a list of credential records.

    Parameters:
    ------------
        connection_id: UUID (Optional)
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
            connection_id=str(connection_id) if connection_id else None,
            role=role,
            state=back_to_v1_credential_state(state) if state else None,
            thread_id=str(thread_id) if thread_id else None,
        )

        bound_logger.debug("Fetching v2 records")
        v2_records = await IssueCredentialFacades.v2.value.get_records(
            controller=aries_controller,
            connection_id=str(connection_id) if connection_id else None,
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


@router.get("/{credential_id}", response_model=CredentialExchange)
async def get_credential(
    credential_id: str,
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """
        Get a credential by credential id.

    Parameters:
    -----------
        credential_id: str
            credential identifier

    Returns:
    --------
        payload: CredentialExchange
            The credential exchange record
    """
    bound_logger = logger.bind(body={"credential_id": credential_id})
    bound_logger.info("GET request received: Get credentials by credential id")

    issuer = issuer_from_id(credential_id)

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Getting credential record")
        result = await issuer.get_record(
            controller=aries_controller, credential_exchange_id=credential_id
        )

    if result:
        bound_logger.info("Successfully fetched credential.")
    else:
        bound_logger.info("No credential returned.")
    return result


@router.post("", response_model=CredentialExchange)
async def send_credential(
    credential: SendCredential,
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """
        Create and send a credential. Automating the entire flow.

    Parameters:
    ------------
        credential: Credential
            payload for sending a credential

    Returns:
    --------
        payload: CredentialExchange
            The response object from sending a credential
        status_code: 200
    """
    bound_logger = logger.bind(body=credential)
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
        except ApiException as e:
            logger.warning(
                "An ApiException was caught while sending credentials, with message `{}`.",
                e.reason,
            )
            raise CloudApiException(
                f"Failed to create or send credential: {e.reason}", e.status
            ) from e

    if result:
        bound_logger.info("Successfully sent credential.")
    else:
        bound_logger.warning("No result from sending credential.")
    return result


@router.post("/create-offer", response_model=CredentialExchange)
async def create_offer(
    credential: CreateOffer,
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """
        Create a credential offer not bound to any connection.

    Parameters:
    ------------
        credential: Credential
            payload for sending a credential

    Returns:
    --------
        The response object from sending a credential
    """
    bound_logger = logger.bind(body=credential)
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


@router.delete("/{credential_exchange_id}", status_code=204)
async def remove_credential_exchange_record(
    credential_exchange_id: str,
    auth: AcaPyAuth = Depends(acapy_auth),
) -> None:
    """
        Remove a credential exchange record.

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


@router.post("/revoke", status_code=204)
async def revoke_credential(
    body: RevokeCredential,
    auth: AcaPyAuth = Depends(acapy_auth),
) -> None:
    """
        Revoke a credential.

    Parameters:
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


@router.post("/publish-revocations", status_code=204)
async def publish_revocations(
    publish_request: PublishRevocationsRequest,
    auth: AcaPyAuth = Depends(acapy_auth),
) -> None:
    """
        Write batch of pending revocations to ledger.

        If no revocation registry id is provided, all pending revocations
        will be published.

        If no credential revocation id is provided, all pending revocations
        for the given revocation registry id will be published.

    Parameters:
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


@router.post("/clear-pending-revocations", response_model=ClearPendingRevocationsResult)
async def clear_pending_revocations(
    clear_pending_request: ClearPendingRevocationsRequest,
    auth: AcaPyAuth = Depends(acapy_auth),
) -> ClearPendingRevocationsResult:
    """
        Clear pending revocations.

        If no revocation registry id is provided, all pending revocations
        will be cleared.

        If no credential revocation id is provided, all pending revocations
        for the given revocation registry id will be cleared.

    Parameters:
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


@router.get("/revocation/record", response_model=IssuerCredRevRecord)
async def get_credential_revocation_record(
    credential_exchange_id: Optional[str] = None,
    credential_revocation_id: Optional[str] = None,
    revocation_registry_id: Optional[str] = None,
    auth: AcaPyAuth = Depends(acapy_auth),
) -> IssuerCredRevRecord:
    """
        Get a credential revocation record.

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


@router.post("/{credential_id}/request", response_model=CredentialExchange)
async def request_credential(
    credential_id: str,
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """
        Send a credential request.

    Parameters:
    -----------
        credential_id: str
            the credential id
    """
    bound_logger = logger.bind(body={"credential_id": credential_id})
    bound_logger.info("POST request received: Send credential request")

    issuer = issuer_from_id(credential_id)

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Fetching records")
        record = await issuer.get_record(aries_controller, credential_id)

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
            controller=aries_controller, credential_exchange_id=credential_id
        )

    if result:
        bound_logger.info("Successfully sent credential request.")
    else:
        bound_logger.warning("No result from sending credential request.")
    return result


@router.post("/{credential_id}/store", response_model=CredentialExchange)
async def store_credential(
    credential_id: str,
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """
        Store a credential.

    Parameters:
    -----------
        credential_id: str
            credential identifier

    """
    bound_logger = logger.bind(body={"credential_id": credential_id})
    bound_logger.info("POST request received: Store credential")

    issuer = issuer_from_id(credential_id)

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Storing credential")
        result = await issuer.store_credential(
            controller=aries_controller, credential_exchange_id=credential_id
        )

    if result:
        bound_logger.info("Successfully stored credential.")
    else:
        bound_logger.warning("No result from storing credential.")
    return result
