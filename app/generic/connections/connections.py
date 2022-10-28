import logging
from typing import List, Optional

from aries_cloudcontroller import (
    AcaPyClient,
    CreateInvitationRequest,
    InvitationMessage,
    InvitationRecord,
    InvitationResult,
    ReceiveInvitationRequest,
)
from aries_cloudcontroller.model.attachment_def import AttachmentDef
from aries_cloudcontroller.model.invitation_create_request import (
    InvitationCreateRequest,
)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from shared_models import conn_record_to_connection, Connection, OobRecord
from app.dependencies import agent_selector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generic/connections", tags=["connections"])


class ConnectToPublicDid(BaseModel):
    public_did: str


class CreateInvitation(BaseModel):
    alias: Optional[str] = None
    multi_use: Optional[bool] = None
    use_public_did: Optional[bool] = None


class AcceptInvitation(BaseModel):
    alias: Optional[str] = None
    use_existing_connection: Optional[bool] = None
    invitation: ReceiveInvitationRequest


class CreateOobInvitation(BaseModel):
    alias: Optional[str] = None
    multi_use: Optional[bool] = None
    use_public_did: Optional[bool] = None
    attachments: Optional[List[AttachmentDef]] = None
    create_connection: Optional[bool] = None


class AcceptOobInvitation(BaseModel):
    alias: Optional[str] = None
    use_existing_connection: Optional[bool] = None
    invitation: InvitationMessage


@router.post("/oob/create-invitation", response_model=InvitationRecord)
async def create_oob_invitation(
    body: CreateOobInvitation = CreateOobInvitation(),
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Create connection invitation out-of-band.
    """

    handshake_protocols = [
        "https://didcomm.org/didexchange/1.0",
        "https://didcomm.org/connections/1.0",
    ]

    if not body.create_connection and (
        not body.attachments or len(body.attachments) == 0
    ):
        raise HTTPException(
            status_code=400,
            detail="Either or both of 'create_connection' and 'attachments' must be defined / true",
        )

    oob_body = InvitationCreateRequest(
        alias=body.alias,
        attachments=body.attachments,
        handshake_protocols=handshake_protocols if body.create_connection else None,
        use_public_did=body.use_public_did,
    )

    invitation = await aries_controller.out_of_band.create_invitation(
        multi_use=body.multi_use,
        body=oob_body,
        auto_accept=True,
    )
    # If the trust registry is not derived but an entity providing this information,
    # we should possibly write the (multi-use) invitation to the registry
    # We could also investigate storing the invitation URL with the OP's DID
    return invitation


@router.post("/oob/accept-invitation", response_model=OobRecord)
async def accept_oob_invitation(
    body: AcceptOobInvitation,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Receive out-of-band invitation.
    """

    oob_record = await aries_controller.out_of_band.receive_invitation(
        auto_accept=True,
        use_existing_connection=body.use_existing_connection,
        alias=body.alias,
        body=body.invitation,
    )
    return oob_record


@router.post("/oob/connect-public-did", response_model=Connection)
async def connect_to_public_did(
    body: ConnectToPublicDid,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Use a public DID as implicit invitation and connect.

    Parameters:
    -----------
    their_public_did: str
        The public did of the entity you want to connect to

    body: CreateConnFromDIDRequest (optional)
        Extra information about the connection request

    Returns:
    ------------
    ConnRecord
        The connection record
    """
    conn_record = await aries_controller.did_exchange.create_request(
        their_public_did=body.public_did
    )

    return conn_record_to_connection(conn_record)


@router.post("/create-invitation", response_model=InvitationResult)
async def create_invitation(
    body: CreateInvitation = CreateInvitation(),
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Create connection invitation.
    """
    invitation = await aries_controller.connection.create_invitation(
        alias=body.alias,
        auto_accept=True,
        multi_use=body.multi_use,
        public=body.use_public_did,
        body=CreateInvitationRequest(),
    )
    return invitation


@router.post("/accept-invitation", response_model=Connection)
async def accept_invitation(
    body: AcceptInvitation,
    aries_controller: AcaPyClient = Depends(agent_selector),
) -> Connection:
    """
    Accept connection invitation.

    Parameters:
    ------------
    invitation: ReceiveInvitationRequest
        the invitation object obtained from create_invitation.
    """

    connection_record = await aries_controller.connection.receive_invitation(
        body=body.invitation,
        auto_accept=True,
        alias=body.alias,
    )
    return conn_record_to_connection(connection_record)


@router.get("/", response_model=List[Connection])
async def get_connections(
    aries_controller: AcaPyClient = Depends(agent_selector),
) -> List[Connection]:
    """
    Retrieve list of connections.

    Returns:
    ---------
    JSON object with “connections” (key), a list of connections (ids)
    """
    connections = await aries_controller.connection.get_connections()

    if connections.results:
        return [
            conn_record_to_connection(connection) for connection in connections.results
        ]

    return []


@router.get("/{connection_id}", response_model=Connection)
async def get_connection_by_id(
    connection_id: str,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Retrieve connection by id.

    Parameters:
    -----------
    connection_id: str

    """
    connection = await aries_controller.connection.get_connection(conn_id=connection_id)
    return conn_record_to_connection(connection)


@router.delete("/{connection_id}")
async def delete_connection_by_id(
    connection_id: str,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Delete connection by id.

    Parameters:
    -----------
    connection_id: str

    Returns:
    ------------
    Empty dict: {}
    """
    await aries_controller.connection.delete_connection(conn_id=connection_id)

    return {}
