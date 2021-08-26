import logging

from aries_cloudcontroller import AriesAgentControllerBase
from dependencies import agent_selector
from fastapi import APIRouter, Depends

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/generic/connections", tags=["connections"])


@router.get("/create-invite")
async def create_invite(
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    """
    Create connection invite.
    """
    invite = await aries_controller.connections.create_invitation()
    return invite


@router.post("/accept-invite")
async def accept_invite(
    invite: dict,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    """
    Accept connection invite.

    Parameters:
    ------------
    invite: dict
        the invitation object obtained from create_invite.
    """
    accept_invite_res = await aries_controller.connections.receive_invitation(invite)
    return accept_invite_res


@router.get("/")
async def get_connections(
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    """
    Retrieve list of connections.

    Returns:
    ---------
    JSON object with “connections” (key), a list of connections (ids)
    """
    connections = await aries_controller.connections.get_connections()
    return connections


@router.get("/{conn_id}")
async def get_connection_by_id(
    connection_id: str,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    """
    Retrieve connection by id.

    Parameters:
    -----------
    connection_id: str

    """
    connection = await aries_controller.connections.get_connection(connection_id)
    return connection


@router.delete("/{conn_id}")
async def delete_connection_by_id(
    connection_id: str,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
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
    remove_res = await aries_controller.connections.remove_connection(connection_id)
    return remove_res
