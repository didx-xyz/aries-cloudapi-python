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
    pass


@router.post("/accept-invite", tags=["connections", "accept"])
async def create_connection(
    aries_controller: AriesAgentControllerBase = Depends(yoma_agent),
):
    pass


@router.get("/connections", tags=["connections"])
async def get_connections(
    aries_controller: AriesAgentControllerBase = Depends(yoma_agent),
):
    pass


@router.get("/connections/{conn_id}", tags=["connections"])
async def get_connection_by_id(
    aries_controller: AriesAgentControllerBase = Depends(yoma_agent),
):
    pass
