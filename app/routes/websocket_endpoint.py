from fastapi import APIRouter, Depends, Query, WebSocket

from app.dependencies.auth import AcaPyAuthVerified
from app.services.websocket import handle_websocket, websocket_auth
from shared.log_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


group_id_query = Query(default="", description="Group ID to which the wallet belongs")


@router.websocket("/v1/ws/")
async def websocket_endpoint_wallet(
    websocket: WebSocket,
    group_id: str = group_id_query,
    auth: AcaPyAuthVerified = Depends(websocket_auth),
):
    logger.info("Received websocket request on group `{}`", group_id)
    await handle_websocket(
        websocket, group_id=group_id, wallet_id="", topic="", auth=auth
    )


@router.websocket("/v1/ws/{wallet_id}")
async def websocket_endpoint_wallet(
    websocket: WebSocket,
    wallet_id: str,
    group_id: str = group_id_query,
    auth: AcaPyAuthVerified = Depends(websocket_auth),
):
    logger.info(
        "Received websocket request on group `{}` and wallet id `{}`",
        group_id,
        wallet_id,
    )
    await handle_websocket(
        websocket, group_id=group_id, wallet_id=wallet_id, topic="", auth=auth
    )


@router.websocket("/v1/ws/topic/{topic}")
async def websocket_endpoint_topic(
    websocket: WebSocket,
    topic: str,
    group_id: str = group_id_query,
    auth: AcaPyAuthVerified = Depends(websocket_auth),
):
    logger.info(
        "Received websocket request on group `{}` and topic `{}`", group_id, topic
    )
    await handle_websocket(
        websocket, group_id=group_id, wallet_id="", topic=topic, auth=auth
    )


@router.websocket("/v1/ws/{wallet_id}/{topic}")
async def websocket_endpoint_wallet_topic(
    websocket: WebSocket,
    wallet_id: str,
    topic: str,
    group_id: str = group_id_query,
    auth: AcaPyAuthVerified = Depends(websocket_auth),
):
    logger.info(
        "Received websocket request for group `{}`, wallet id `{}`, and topic `{}`",
        group_id,
        wallet_id,
        topic,
    )
    await handle_websocket(
        websocket, group_id=group_id, wallet_id=wallet_id, topic=topic, auth=auth
    )
