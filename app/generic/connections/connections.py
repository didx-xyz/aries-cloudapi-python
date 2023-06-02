import logging
from typing import List, Optional

from aries_cloudcontroller import (
    AcaPyClient,
    CreateInvitationRequest,
    InvitationResult,
    ReceiveInvitationRequest,
)
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.dependencies import agent_selector
from shared import Connection, conn_record_to_connection

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


@router.post("/create-invitation", response_model=InvitationResult)
async def create_invitation(
    body: Optional[CreateInvitation] = None,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Create connection invitation.
    """
    if body is None:
        body = CreateInvitation()

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


@router.get("", response_model=List[Connection])
async def get_connections(
    aries_controller: AcaPyClient = Depends(agent_selector),
) -> List[Connection]:
    """
    Retrieve list of connections.

    Returns:
    ---------
    JSON object with connections (key), a list of connections (ids)
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
