import logging
from typing import Optional

from aiohttp import ClientResponseError
from fastapi import APIRouter, Depends, Query

from app.dependencies.acapy_client_roles_container import client_from_auth
from app.dependencies.auth import AcaPyAuth, acapy_auth
from app.facades import revocation_registry
from app.facades.acapy_ledger import schema_id_from_credential_definition_id
from app.facades.acapy_wallet import assert_public_did
from app.facades.trust_registry import assert_valid_issuer
from app.generic.issuer.models import (
    CreateOffer,
    Credential,
    CredentialNoConnection,
    IssueCredentialFacades,
    RevokeCredential,
    SendCredential,
    issuer_from_id,
    issuer_from_protocol_version,
)
from app.util.did import did_from_credential_definition_id
from shared.cloud_api_error import CloudApiException
from shared.models.topics.base import CredentialExchange

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generic/issuer", tags=["issuer"])


@router.get("/credentials")
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

    async with client_from_auth(auth) as aries_controller:
        v1_records = await IssueCredentialFacades.v1.value.get_records(
            controller=aries_controller, connection_id=connection_id
        )

        v2_records = await IssueCredentialFacades.v2.value.get_records(
            controller=aries_controller, connection_id=connection_id
        )

    return v1_records + v2_records


@router.get("/credentials/{credential_id}")
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

    issuer = issuer_from_id(credential_id)

    async with client_from_auth(auth) as aries_controller:
        return await issuer.get_record(
            controller=aries_controller, credential_exchange_id=credential_id
        )


@router.post("/credentials", response_model=CredentialExchange)
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

    issuer = issuer_from_protocol_version(credential.protocol_version)

    async with client_from_auth(auth) as aries_controller:
        # Assert the agent has a public did
        public_did = await assert_public_did(aries_controller)

        # Retrieve the schema_id based on the credential definition id
        schema_id = await schema_id_from_credential_definition_id(
            aries_controller, credential.credential_definition_id
        )

        # Make sure we are allowed to issue according to trust registry rules
        await assert_valid_issuer(public_did, schema_id)

        try:
            return await issuer.send_credential(
                controller=aries_controller,
                credential=Credential(
                    attributes=credential.attributes,
                    cred_def_id=credential.credential_definition_id,
                    connection_id=credential.connection_id,
                ),
            )
        except ClientResponseError as e:
            logger.debug(
                "A ClientResponseError was caught while sending credentials. The error message is: '%s'",
                e.message,
            )
            raise CloudApiException("Failed to create and send credential.", 500) from e


@router.post("/credentials/create-offer")
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

    issuer = issuer_from_protocol_version(credential.protocol_version)

    async with client_from_auth(auth) as aries_controller:
        # Assert the agent has a public did
        public_did = await assert_public_did(aries_controller)

        # Retrieve the schema_id based on the credential definition id
        schema_id = await schema_id_from_credential_definition_id(
            aries_controller, credential.credential_definition_id
        )

        # Make sure we are allowed to issue according to trust registry rules
        await assert_valid_issuer(public_did, schema_id)

        return await issuer.create_offer(
            controller=aries_controller,
            credential=CredentialNoConnection(
                attributes=credential.attributes,
                cred_def_id=credential.credential_definition_id,
            ),
        )


@router.delete("/credentials/{credential_id}", status_code=204)
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
    issuer = issuer_from_id(credential_id)

    async with client_from_auth(auth) as aries_controller:
        await issuer.delete_credential(
            controller=aries_controller, credential_exchange_id=credential_id
        )


@router.post("/credentials/revoke", status_code=204)
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

    async with client_from_auth(auth) as aries_controller:
        await revocation_registry.revoke_credential(
            controller=aries_controller,
            credential_exchange_id=body.credential_exchange_id,
            auto_publish_to_ledger=body.auto_publish_on_ledger,
            credential_definition_id=body.credential_definition_id,
        )


@router.post("/credentials/{credential_id}/request")
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
    issuer = issuer_from_id(credential_id)

    async with client_from_auth(auth) as aries_controller:
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

        return await issuer.request_credential(
            controller=aries_controller, credential_exchange_id=credential_id
        )


@router.post("/credentials/{credential_id}/store")
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
    issuer = issuer_from_id(credential_id)

    async with client_from_auth(auth) as aries_controller:
        return await issuer.store_credential(
            controller=aries_controller, credential_exchange_id=credential_id
        )
