from fastapi import APIRouter, Depends, WebSocket

from app.dependencies.auth import AcaPyAuthVerified
from app.services.websocket import handle_websocket, websocket_auth
from shared.log_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.websocket("/ws/topic/{topic}")
async def websocket_endpoint_topic(
    websocket: WebSocket,
    topic: str,
    auth: AcaPyAuthVerified = Depends(websocket_auth),
):
    logger.info("Received websocket request on topic `{}`", topic)
    await handle_websocket(websocket, wallet_id="", topic=topic, auth=auth)


@router.websocket("/ws/{wallet_id}")
async def websocket_endpoint_wallet(
    websocket: WebSocket,
    wallet_id: str,
    auth: AcaPyAuthVerified = Depends(websocket_auth),
):
    logger.info("Received websocket request on wallet id `{}`", wallet_id)
    await handle_websocket(websocket, wallet_id=wallet_id, topic="", auth=auth)


@router.websocket("/ws/{wallet_id}/{topic}")
async def websocket_endpoint_wallet_topic(
    websocket: WebSocket,
    wallet_id: str,
    topic: str,
    auth: AcaPyAuthVerified = Depends(websocket_auth),
):
    logger.info(
        "Received websocket request on wallet id `{}` and topic `{}`", wallet_id, topic
    )
    await handle_websocket(websocket, wallet_id=wallet_id, topic=topic, auth=auth)
