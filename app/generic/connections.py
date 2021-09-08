import logging
from typing import Optional

from aries_cloudcontroller import (
    AcaPyClient,
    InvitationResult,
    ReceiveInvitationRequest,
    ConnRecord,
    ConnectionList,
    CreateInvitationRequest,
)
from dependencies import agent_selector
from fastapi import APIRouter, Depends

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/generic/connections", tags=["connections"])


# TODO this should be a post request
@router.get("/create-invite", response_model=InvitationResult)
async def create_invite(
    alias: Optional[str] = None,
    auto_accept: Optional[bool] = None,
    multi_use: Optional[bool] = None,
    public: Optional[bool] = None,
    create_invitation_request: Optional[CreateInvitationRequest] = {},
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Create connection invite.
    """
    invite = await aries_controller.connection.create_invitation(
        alias=alias,
        auto_accept=auto_accept,
        multi_use=multi_use,
        public=public,
        body=create_invitation_request,
    )
    return invite


@router.post("/accept-invite", response_model=ConnRecord)
async def accept_invite(
    invite: ReceiveInvitationRequest,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Accept connection invite.

    Parameters:
    ------------
    invite: ReceiveInvitationRequest
        the invitation object obtained from create_invite.
    """

    conn_record = await aries_controller.connection.receive_invitation(body=invite)
    return conn_record


@router.get("/", response_model=ConnectionList)
async def get_connections(
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Retrieve list of connections.

    Returns:
    ---------
    JSON object with “connections” (key), a list of connections (ids)
    """
    connections = await aries_controller.connection.get_connections()
    return connections


@router.get("/{conn_id}", response_model=ConnRecord)
async def get_connection_by_id(
    conn_id: str,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Retrieve connection by id.

    Parameters:
    -----------
    conn_id: str

    """
    connection = await aries_controller.connection.get_connection(conn_id=conn_id)
    return connection


@router.delete("/{conn_id}")
async def delete_connection_by_id(
    conn_id: str,
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
    remove_res = await aries_controller.connection.delete_connection(conn_id=conn_id)
    return remove_res
