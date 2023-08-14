from typing import List, Optional

from aiohttp import ClientResponseError
from fastapi import APIRouter, Depends, Query

from app.dependencies.acapy_clients import client_from_auth
from app.dependencies.auth import AcaPyAuth, acapy_auth
from app.exceptions.cloud_api_error import CloudApiException
from app.models.issuer import (
    CreateOffer,
    CredentialBase,
    CredentialType,
    RevokeCredential,
    SendCredential,
)
from app.services import revocation_registry
from app.services.acapy_ledger import schema_id_from_credential_definition_id
from app.services.acapy_wallet import assert_public_did
from app.services.trust_registry import assert_valid_issuer
from app.util.acapy_issuer_utils import (
    IssueCredentialFacades,
    issuer_from_id,
    issuer_from_protocol_version,
)
from app.util.did import did_from_credential_definition_id
from shared.log_config import get_logger
from shared.models.topics import CredentialExchange

logger = get_logger(__name__)

router = APIRouter(prefix="/generic/issuer/credentials", tags=["issuer"])


@router.get("", response_model=List[CredentialExchange])
async def get_credentials(
    connection_id: Optional[str] = Query(None),
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """
        Get a list of credential records.

    Parameters:
    ------------
        connection_id: str (Optional)
    """
    bound_logger = logger.bind(body={"connection_id": connection_id})
    bound_logger.info("GET request received: Get credentials")

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Fetching v1 records")
        v1_records = await IssueCredentialFacades.v1.value.get_records(
            controller=aries_controller, connection_id=connection_id
        )

        bound_logger.debug("Fetching v2 records")
        v2_records = await IssueCredentialFacades.v2.value.get_records(
            controller=aries_controller, connection_id=connection_id
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
        public_did = await assert_public_did(aries_controller)

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
        except ClientResponseError as e:
            logger.warning(
                "ClientResponseError was caught while sending credentials, with message `{}`.",
                e.message,
            )
            raise CloudApiException(
                f"Failed to create or send credential: {e}", 500
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
        public_did = await assert_public_did(aries_controller)

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


@router.delete("/{credential_id}", status_code=204)
async def remove_credential(
    credential_id: str,
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """
        Remove a credential.

    Parameters:
    -----------
        credential_id: str
            credential identifier

    Returns:
    --------
        payload: None
        status_code: 204
    """
    bound_logger = logger.bind(body={"credential_id": credential_id})
    bound_logger.info("DELETE request received: Remove credential by id")

    issuer = issuer_from_id(credential_id)

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Deleting credential")
        await issuer.delete_credential(
            controller=aries_controller, credential_exchange_id=credential_id
        )

    bound_logger.info("Successfully deleted credential by id.")


@router.post("/revoke", status_code=204)
async def revoke_credential(
    body: RevokeCredential,
    auth: AcaPyAuth = Depends(acapy_auth),
):
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

        if not record.credential_definition_id or not record.schema_id:
            raise CloudApiException(
                "Record has no credential definition or schema associated. "
                "This probably means you haven't received an offer yet.",
                412,
            )

        did = did_from_credential_definition_id(record.credential_definition_id)

        # Make sure the issuer is allowed to issue this credential according to trust registry rules
        await assert_valid_issuer(f"did:sov:{did}", record.schema_id)

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
