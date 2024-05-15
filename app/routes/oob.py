from typing import Optional

from aries_cloudcontroller import InvitationCreateRequest, InvitationRecord, OobRecord
from fastapi import APIRouter, Depends

from app.dependencies.acapy_clients import client_from_auth
from app.dependencies.auth import AcaPyAuth, acapy_auth_from_header
from app.exceptions import handle_acapy_call, handle_model_with_validation
from app.models.oob import AcceptOobInvitation, ConnectToPublicDid, CreateOobInvitation
from app.util.credentials import strip_protocol_prefix
from shared.log_config import get_logger
from shared.models.connection_record import Connection, conn_record_to_connection

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/oob", tags=["out-of-band"])


@router.post("/create-invitation", response_model=InvitationRecord)
async def create_oob_invitation(
    body: Optional[CreateOobInvitation] = None,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> InvitationRecord:
    """
    Create an out-of-band invitation.
    ------------------------------

    The attachment field is used to include a credential offer or a proof request in the invitation.
    The attachment ID is the credential ID or proof request ID without the protocol prefix.
    The attachment type is either "credential-offer" or "present-proof".

    The multi_use field is used to determine if the invitation can be used multiple times by different tenants.
    The use_public_did field is used to determine if the invitation should use the public DID to create a connection.


    Request body:
    -------------
        body:CreateOobInvitation
            alias: Optional[str]
            multi_use: Optional[bool]
            use_public_did: Optional[bool]
            attachments: Optional[List[Attachment]]
            handshake_protocols: Optional[List[str]]
            create_connection: Optional[bool]

    Returns:
    --------
        InvitationRecord
            The invitation record
    """
    bound_logger = logger.bind(body=body)
    bound_logger.info("POST request received: Create OOB invitation")
    if body is None:
        body = CreateOobInvitation()

    handshake_protocols = (
        [
            "https://didcomm.org/didexchange/1.0",
            "https://didcomm.org/connections/1.0",
        ]
        if body.create_connection
        else None
    )

    if body.attachments:
        for item in body.attachments:
            if item.id:  # Optional field
                item.id = strip_protocol_prefix(item.id)

    oob_body = handle_model_with_validation(
        logger=bound_logger,
        model_class=InvitationCreateRequest,
        alias=body.alias,
        attachments=body.attachments,
        handshake_protocols=handshake_protocols,
        use_public_did=body.use_public_did,
    )

    bound_logger.debug("Creating invitation")
    async with client_from_auth(auth) as aries_controller:
        invitation = await handle_acapy_call(
            logger=bound_logger,
            acapy_call=aries_controller.out_of_band.create_invitation,
            multi_use=body.multi_use,
            body=oob_body,
            auto_accept=True,
        )
    # If the trust registry is not derived but an entity providing this information,
    # we should possibly write the (multi-use) invitation to the registry
    # We could also investigate storing the invitation URL with the OP's DID
    bound_logger.info("Successfully created invitation.")
    return invitation


@router.post("/accept-invitation", response_model=OobRecord)
async def accept_oob_invitation(
    body: AcceptOobInvitation,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> OobRecord:
    """
    Accept out-of-band invitation.
    ------------------------------

    As with the connection endpoint, the invitation object from the create-invitation endpoint
    is passed to this endpoint. The base64 encoded invitation url (from create-invitation) can also
    be decoded and passed as the invitation object.

    Request body:
    -------------
        body: AcceptOobInvitation
            alias: Optional[str]
            use_existing_connection: Optional[bool]
            invitation: InvitationMessage


    Returns:
    --------
        OobRecord
            The out-of-band record
    """
    bound_logger = logger.bind(body=body)
    bound_logger.info("POST request received: Accept OOB invitation")

    async with client_from_auth(auth) as aries_controller:
        oob_record = await handle_acapy_call(
            logger=bound_logger,
            acapy_call=aries_controller.out_of_band.receive_invitation,
            auto_accept=True,
            use_existing_connection=body.use_existing_connection,
            alias=body.alias,
            body=body.invitation,
        )
    bound_logger.info("Successfully accepted invitation.")
    return oob_record


@router.post("/connect-public-did", response_model=Connection)
async def connect_to_public_did(
    body: ConnectToPublicDid,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> Connection:
    """
    Connect using public DID as implicit invitation.
    -----------------------------------------------

    Connection will automatically be established with the tenant of public DID.

    Request body:
    -------------
        body: ConnectToPublicDid
            public_did: str

    Returns:
    ---
        Connection
            The connection exchange record
    """
    bound_logger = logger.bind(body=body)
    bound_logger.info("POST request received: Connect to public DID")
    async with client_from_auth(auth) as aries_controller:
        conn_record = await handle_acapy_call(
            logger=bound_logger,
            acapy_call=aries_controller.did_exchange.create_request,
            their_public_did=body.public_did,
        )

    result = conn_record_to_connection(conn_record)
    bound_logger.info("Successfully created DID exchange request.")
    return result
