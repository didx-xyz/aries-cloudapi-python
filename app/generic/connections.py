import logging

from aries_cloudcontroller import AriesAgentControllerBase
from dependencies import agent_selector
from fastapi import APIRouter, Depends

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/generic/connections", tags=["connections"])


@router.get("/create-invite", tags=["connections", "create"])
async def create_invite(
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    invite = await aries_controller.connections.create_invitation()
    return invite


@router.post("/accept-invite", tags=["connections", "accept"])
async def accept_invite(
    invite: dict,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    accept_invite_res = await aries_controller.connections.receive_invitation(invite)
    return accept_invite_res


@router.get("/", tags=["connections"])
async def get_connections(
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    connections = await aries_controller.connections.get_connections()
    return connections


@router.get("/{conn_id}", tags=["connections"])
async def get_connection_by_id(
    connection_id: str,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    connection = await aries_controller.connections.get_connection(connection_id)
    return connection


@router.delete("/{conn_id}", tags=["connections"])
async def delete_connection_by_id(
    connection_id: str,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    remove_res = await aries_controller.connections.remove_connection(connection_id)
    return remove_res
