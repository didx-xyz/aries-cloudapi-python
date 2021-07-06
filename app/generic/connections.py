import logging

from fastapi import APIRouter, HTTPException, Depends
from aries_cloudcontroller import AriesAgentControllerBase

from dependencies import yoma_agent

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/generic/connections", tags=["connections"])


@router.get("/create-invite", tags=["connections", "create"])
async def create_connection(
    aries_controller: AriesAgentControllerBase = Depends(yoma_agent),
):
    invite = await aries_controller.connections.create_invitation()
    return invite


@router.post("/accept-invite", tags=["connections", "accept"])
async def accept_invite(
    invite: dict,
    aries_controller: AriesAgentControllerBase = Depends(yoma_agent),
):
    accept_invite_res = await aries_controller.connections.accept_connection(invite)
    return accept_invite_res


@router.get("/connections", tags=["connections"])
async def get_connections(
    aries_controller: AriesAgentControllerBase = Depends(yoma_agent),
):
    connections = await aries_controller.connections.get_connection()
    return connections


@router.get("/connections/{conn_id}", tags=["connections"])
async def get_connection_by_id(
    conn_id: str,
    aries_controller: AriesAgentControllerBase = Depends(yoma_agent),
):
    connection = await aries_controller.connections.get_connection(conn_id)
    return connection


@router.post("/connections/{conn_id}", tags=["connections"])
async def delete_connection_by_id(
    conn_id: str, aries_controller: AriesAgentControllerBase = Depends(yoma_agent)
):
    remove_res = await aries_controller.connections.remove_connection(conn_id)
    return remove_res
