import asyncio
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
    RevokedResponse,
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
from app.util.pagination import limit_query_parameter, offset_query_parameter
from app.util.retry_method import coroutine_with_retry_until_value
from shared.log_config import get_logger
from shared.models.credential_exchange import (
    CredentialExchange,
    Role,
    State,
    back_to_v1_credential_state,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/issuer/credentials", tags=["issuer"])


@router.post("", summary="Send Holder a Credential", response_model=CredentialExchange)
async def send_credential(
    credential: SendCredential,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> CredentialExchange:
    """
    Create and send a credential, automating the issuer-side flow
    ---
    NB: Only a tenant with the issuer role can send credentials.

    When creating a credential, the credential type must be one of `indy` or `ld_proof`.
    ```json
    {
        "type": "indy" or "ld_proof",
        "indy_credential_detail": {...}, <-- Required if type is indy
        "ld_credential_detail": {...}, <-- Required if type is ld_proof
        "save_exchange_record": true, <-- Whether the credential exchange record should be saved on completion.
        "connection_id": "string", <-- The issuer's reference to the connection they want to submit the credential to.
        "protocol_version": "v2" <-- v1 is supported, but deprecated.
    }
    ```
    Setting the `save_exchange_record` field to True will save the exchange record after the credential is accepted.
    The default behaviour is to only save exchange records while they are in pending state.

    For a detailed technical specification of the credential issuing process, refer to the [Aries Issue Credential v2
    RFC](https://github.com/hyperledger/aries-rfcs/blob/main/features/0453-issue-credential-v2/README.md).

    Request Body:
    ---
        credential: SendCredential
            The payload for sending a credential

    Returns:
    ---
        CredentialExchange
            A record of this credential exchange
    """
    bound_logger = logger.bind(
        body={
            # Do not log credential attributes:
            "connection_id": credential.connection_id,
            "protocol_version": credential.protocol_version,
            "credential_type": credential.type,
        }
    )
    bound_logger.debug("POST request received: Send credential")

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

    bound_logger.debug("Successfully sent credential.")
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
    Create a credential offer, not bound to any connection
    ---
    NB: Only a tenant with the issuer role can create credential offers.

    This endpoint takes the same body as the send credential endpoint, but without a connection id. This
    means the credential will not be sent, but it will do the initial step of creating a credential exchange record,
    which the issuer can then use in the out of band (OOB) protocol.

    The OOB protocol allows credentials to be sent over alternative channels, such as email or QR code, where a
    connection does not yet exist between holder and issuer.

    The credential type must be one of indy or ld_proof.
    ```json
    {
        "type": "indy" or "ld_proof",
        "indy_credential_detail": {...}, <-- Required if type is indy
        "ld_credential_detail": {...}, <-- Required if type is ld_proof
        "save_exchange_record": true, <-- Whether the credential exchange record should be saved on completion.
        "protocol_version": "v2" <-- v1 is supported, but deprecated.
    }
    ```
    For a detailed technical specification of the credential issuing process, refer to the [Aries Issue Credential v2
    RFC](https://github.com/hyperledger/aries-rfcs/blob/main/features/0453-issue-credential-v2/README.md).

    Request Body:
    ---
        credential: CreateOffer
            The payload for creating a credential offer

    Returns:
    ---
        CredentialExchange
            A record of this credential exchange
    """
    bound_logger = logger.bind(
        body={
            # Do not log credential attributes:
            "protocol_version": credential.protocol_version,
            "credential_type": credential.type,
        }
    )
    bound_logger.debug("POST request received: Create credential offer")

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

    bound_logger.debug("Successfully created credential offer.")
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
    Sends a request to accept a credential offer
    ---
    The holder uses this endpoint to accept an offer from an issuer.

    In technical terms, when a holder has a credential exchange record with a state 'offer-received', then they can use
    this endpoint to accept that credential offer, and store the credential in their wallet.

    Parameters:
    ---
        credential_exchange_id: str
            The holder's reference to the credential exchange that they want to accept

    Returns:
    ---
        CredentialExchange
            An updated record of this credential exchange
    """
    bound_logger = logger.bind(body={"credential_exchange_id": credential_exchange_id})
    bound_logger.debug("POST request received: Send credential request")

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

    bound_logger.debug("Successfully sent credential request.")
    return result


@router.post(
    "/{credential_exchange_id}/store",
    summary="Store a Received Credential in Wallet",
    response_model=CredentialExchange,
    deprecated=True,
)
async def store_credential(
    credential_exchange_id: str,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> CredentialExchange:
    """
    NB: Deprecated because credentials are automatically stored in wallet after they are accepted
    ---

    Store a credential
    ---
    Store a credential by providing the credential exchange id.
    The credential exchange id is the id of the credential exchange record, not the credential itself.

    The holder only needs to call this endpoint if the holder receives a credential out of band

    The holder can store the credential in their wallet after receiving it from the issuer.

    Parameters:
    ---
        credential_exchange_id: str
            credential exchange record identifier

    Returns:
    ---
        CredentialExchange
            An updated record of this credential exchange
    """
    bound_logger = logger.bind(body={"credential_exchange_id": credential_exchange_id})
    bound_logger.debug("POST request received: Store credential")

    issuer = issuer_from_id(credential_exchange_id)

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Storing credential")
        result = await issuer.store_credential(
            controller=aries_controller, credential_exchange_id=credential_exchange_id
        )

    bound_logger.debug("Successfully stored credential.")
    return result


@router.get(
    "",
    summary="Fetch Credential Exchange Records",
    response_model=List[CredentialExchange],
)
async def get_credentials(
    limit: Optional[int] = limit_query_parameter,
    offset: Optional[int] = offset_query_parameter,
    connection_id: Optional[str] = Query(None),
    role: Optional[Role] = Query(None),
    state: Optional[State] = Query(None),
    thread_id: Optional[UUID] = Query(None),
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> List[CredentialExchange]:
    """
    Get a list of credential exchange records
    ---
    Both holders and issuers can call this endpoint, because they each have their own records of a credential exchange.

    These records contain information about the credentials issued to a holder, such as the current state of the
    exchange, and other metadata such as the `connection_id` that a credential was submit to (if an issuer) or received
    from (if a holder). Each record in the list is related to a single credential exchange flow.

    NB: An issuer and a holder will have distinct credential exchange ids, despite referring to the same exchange.
    The `thread_id` is the only record attribute that will be the same for the holder and the issuer.

    An exchange record will automatically be deleted after a flow completes (i.e. when state is 'done'),
    unless the `save_exchange_record` was set to true.

    The following parameters can be set to filter the fetched exchange records: connection_id, role, state, thread_id.

    Parameters (Optional):
    ---
        limit: int - The maximum number of records to retrieve
        offset: int - The offset to start retrieving records from
        connection_id: str
        role: Role: "issuer", "holder"
        state: State: "proposal-sent", "proposal-received", "offer-sent", "offer-received",
                                 "request-sent", "request-received", "credential-issued", "credential-received",
                                 "credential-revoked", "abandoned", "done"
        thread_id: UUID

    Returns:
    ---
        List[CredentialExchange]
            A list of credential exchange records
    """
    bound_logger = logger.bind(body={"connection_id": connection_id})
    bound_logger.debug("GET request received: Get credentials")

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Fetching v1 records")
        v1_records = await IssueCredentialFacades.V1.value.get_records(
            controller=aries_controller,
            limit=limit,
            offset=offset,
            connection_id=connection_id,
            role=role,
            state=back_to_v1_credential_state(state) if state else None,
            thread_id=str(thread_id) if thread_id else None,
        )

        bound_logger.debug("Fetching v2 records")
        v2_records = await IssueCredentialFacades.V2.value.get_records(
            controller=aries_controller,
            limit=limit,
            offset=offset,
            connection_id=connection_id,
            role=role,
            state=state,
            thread_id=str(thread_id) if thread_id else None,
        )

    result = v1_records + v2_records
    if result:
        bound_logger.debug("Successfully fetched v1 and v2 records.")
    else:
        bound_logger.debug("No v1 or v2 records returned.")
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
    Get a credential exchange record by credential id
    ---
    Both holders and issuers can call this endpoint, because they each have their own records of a credential exchange.

    These records contain information about the credentials issued to a holder, such as the current state of the
    exchange, and other metadata such as the `connection_id` that a credential was submit to (if an issuer) or received
    from (if a holder).

    NB: An issuer and a holder will have distinct credential exchange ids, despite referring to the same exchange.
    The `thread_id` is the only record attribute that will be the same for the holder and the issuer.

    An exchange record will automatically be deleted after a flow completes (i.e. when state is 'done'),
    unless the `save_exchange_record` was set to true.

    The following parameters can be set to filter the fetched exchange records: connection_id, role, state, thread_id.

    Parameters:
    ---
        credential_exchange_id: str
            The identifier of the credential exchange record that you want to fetch

    Returns:
    ---
        CredentialExchange
            The credential exchange record
    """
    bound_logger = logger.bind(body={"credential_exchange_id": credential_exchange_id})
    bound_logger.debug("GET request received: Get credentials by credential id")

    issuer = issuer_from_id(credential_exchange_id)

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Getting credential record")
        result = await issuer.get_record(
            controller=aries_controller, credential_exchange_id=credential_exchange_id
        )

    bound_logger.debug("Successfully fetched credential.")
    return result


@router.delete(
    "/{credential_exchange_id}", summary="Delete an Exchange Record", status_code=204
)
async def remove_credential_exchange_record(
    credential_exchange_id: str,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> None:
    """
    Delete a credential exchange record
    ---
    This will remove a specific credential exchange from your storage records.

    Parameters:
    ---
        credential_exchange_id: str
            The identifier of the credential exchange record that you want to delete

    Returns:
    ---
        status_code: 204
    """
    bound_logger = logger.bind(body={"credential_exchange_id": credential_exchange_id})
    bound_logger.debug(
        "DELETE request received: Remove credential exchange record by id"
    )

    issuer = issuer_from_id(credential_exchange_id)

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Deleting credential")
        await issuer.delete_credential_exchange_record(
            controller=aries_controller, credential_exchange_id=credential_exchange_id
        )

    bound_logger.debug("Successfully deleted credential exchange record.")


@router.post("/revoke", summary="Revoke a Credential (if revocable)")
async def revoke_credential(
    body: RevokeCredential,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> RevokedResponse:
    """
    Revoke a credential
    ---
    Revoke a credential by providing the identifier of the exchange.

    If an issuer is going to revoke more than one credential, it is recommended to set the
    'auto_publish_on_ledger' field to False (default), and then batch publish the revocations using
    the 'publish-revocations' endpoint.

    By batching the revocations, the issuer can save on transaction fees related to
    publishing revocations to the ledger.

    Request Body:
    ---
        body: RevokeCredential
            - credential_exchange_id (str): The ID associated with the credential exchange that should be revoked.
            - auto_publish_on_ledger (bool): (True) publish revocation to ledger immediately, or
                (default, False) mark it pending

    Returns:
    ---
        RevokedResponse:
            revoked_cred_rev_ids:
              The revocation registry indexes that were revoked.
              Will be empty if the revocation was marked as pending.
    """
    bound_logger = logger.bind(body=body)
    bound_logger.debug("POST request received: Revoke credential")

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Revoking credential")
        result = await revocation_registry.revoke_credential(
            controller=aries_controller,
            credential_exchange_id=body.credential_exchange_id,
            auto_publish_to_ledger=body.auto_publish_on_ledger,
        )

    bound_logger.info("Successfully revoked credential.")
    return result


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
    Get a credential revocation record
    ---
    Fetch a credential revocation record by providing the credential exchange id.
    Records can also be fetched by providing the credential revocation id and revocation registry id.

    The record is the payload of the webhook event on topic 'issuer_cred_rev', and contains the credential's revocation
    status and other metadata.

    The revocation registry id (rev_reg_id) and credential revocation id (cred_rev_id) can be found
    in this record if you have the credential exchange id.

    Parameters:
    ---
        credential_exchange_id: str
        credential_revocation_id: str
        revocation_registry_id: str

    Returns:
    ---
        IssuerCredRevRecord
            The credential revocation record

    Raises:
    ---
        CloudApiException: 400
            If credential_exchange_id is not provided, both credential_revocation_id and revocation_registry_id must be.
    """
    bound_logger = logger.bind(
        body={
            "credential_exchange_id": credential_exchange_id,
            "credential_revocation_id": credential_revocation_id,
            "revocation_registry_id": revocation_registry_id,
        }
    )
    bound_logger.debug("GET request received: Get credential revocation record by id")

    if credential_exchange_id is None and (
        credential_revocation_id is None or revocation_registry_id is None
    ):
        raise CloudApiException(
            "If credential_exchange_id is not provided then both "
            "credential_revocation_id and revocation_registry_id must be provided.",
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

    bound_logger.debug("Successfully fetched credential revocation record.")
    return revocation_record


@router.post("/publish-revocations", summary="Publish Pending Revocations")
async def publish_revocations(
    publish_request: PublishRevocationsRequest,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> RevokedResponse:
    """
    Write pending revocations to the ledger
    ---
    Revocations that are in a pending state can be published to the ledger.

    The endpoint accepts a `revocation_registry_credential_map`, which provides a dictionary of
    revocation registry IDs to credential revocation IDs, to allow publishing individual credentials.

    If no revocation registry id is provided (i.e. an empty map `revocation_registry_credential_map: {}`),
    then all pending revocations will be published.

    If no credential revocation id is provided under a given revocation registry id, then all pending revocations for
    the given revocation registry id will be published.

    Where to find the revocation registry id and credential revocation id:
    When issuing a credential, against a credential definition that supports revocation,
    the issuer will receive a webhook event on the topic 'issuer_cred_rev'. This event will contain
    the credential exchange id (cred_ex_id), the credential revocation id (cred_rev_id) and
    the revocation registry id (rev_reg_id).

    Request Body:
    ---
        publish_request: PublishRevocationsRequest
            An instance of `PublishRevocationsRequest` containing a `revocation_registry_credential_map`. This map
            is a dictionary where each key is a revocation registry ID and its value is a list of credential
            revocation IDs to be published. Providing an empty list for a registry ID instructs the system to
            publish all pending revocations for that ID. An empty dictionary signifies that all pending
            revocations across all registry IDs should be published.

    Returns:
    ---
        RevokedResponse:
            revoked_cred_rev_ids:
              The revocation registry indexes that were revoked.
              Will be empty if there were no revocations to publish.
    """
    bound_logger = logger.bind(body=publish_request)
    bound_logger.debug("POST request received: Publish revocations")

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Publishing revocations")
        result = await revocation_registry.publish_pending_revocations(
            controller=aries_controller,
            revocation_registry_credential_map=publish_request.revocation_registry_credential_map,
        )

        if not result:
            bound_logger.debug("No revocations to publish.")
            return RevokedResponse()

        endorser_transaction_id = result.txn.transaction_id
        if endorser_transaction_id:
            bound_logger.debug(
                "Wait for publish complete on transaction id: {}",
                endorser_transaction_id,
            )
            try:
                # Wait for transaction to be acknowledged and written to the ledger
                await coroutine_with_retry_until_value(
                    coroutine_func=aries_controller.endorse_transaction.get_transaction,
                    args=(endorser_transaction_id,),
                    field_name="state",
                    expected_value="transaction_acked",
                    logger=bound_logger,
                    max_attempts=30,
                    retry_delay=1,
                )
            except asyncio.TimeoutError as e:
                raise CloudApiException(
                    "Timeout waiting for endorser to accept the revocations request.",
                    504,
                ) from e

    bound_logger.info("Successfully published revocations.")
    return RevokedResponse.model_validate(result.model_dump())


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
    Clear pending revocations
    ---
    Revocations that are in a pending state can be cleared, such that they are no longer set to be revoked.

    The endpoint accepts a `revocation_registry_credential_map`, which provides a dictionary of
    revocation registry IDs to credential revocation IDs, to allow clearing individual credentials.

    If no revocation registry id is provided (i.e. an empty map `revocation_registry_credential_map: {}`),
    then all pending revocations will be cleared.

    If no credential revocation id is provided under a given revocation registry id, then all pending revocations for
    the given revocation registry id will be cleared.

    Where to find the revocation registry id and credential revocation id:
    When issuing a credential, against a credential definition that supports revocation,
    the issuer will receive a webhook event on the topic 'issuer_cred_rev'. This event will contain
    the credential exchange id (cred_ex_id), the credential revocation id (cred_rev_id) and
    the revocation registry id (rev_reg_id).

    Request Body:
    ---
        clear_pending_request: ClearPendingRevocationsRequest
            An instance of `ClearPendingRevocationsRequest` containing a `revocation_registry_credential_map`. This map
            is a dictionary where each key is a revocation registry ID and its value is a list of credential
            revocation IDs to be cleared. Providing an empty list for a registry ID instructs the system to
            clear all pending revocations for that ID. An empty dictionary signifies that all pending
            revocations across all registry IDs should be cleared.

    Returns:
    ---
        ClearPendingRevocationsResult
            The revocations that are still pending after the clear request is performed
    """
    bound_logger = logger.bind(body=clear_pending_request)
    bound_logger.debug("POST request received: Clear pending revocations")

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Clearing pending revocations")
        response = await revocation_registry.clear_pending_revocations(
            controller=aries_controller,
            revocation_registry_credential_map=clear_pending_request.revocation_registry_credential_map,
        )

    bound_logger.debug("Successfully cleared pending revocations.")
    return response
