import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from app.dependencies.auth import (
    AcaPyAuthVerified,
    get_acapy_auth,
    get_acapy_auth_verified,
)
from app.event_handling.websocket_manager import WebsocketManager

LOGGER = logging.getLogger(__name__)
router = APIRouter()


DISCONNECT_CHECK_PERIOD = 0.1


async def get_websocket_api_key(websocket: WebSocket) -> str:
    for header, value in websocket.headers.items():
        if header.lower() == "x-api-key":
            return value
    return ""


async def websocket_auth(
    websocket: WebSocket,
    api_key: str = Depends(get_websocket_api_key),
) -> AcaPyAuthVerified:
    try:
        auth = get_acapy_auth(api_key)
        return get_acapy_auth_verified(auth)
    except HTTPException:
        await websocket.accept()  # Accept to send unauthorized message
        await websocket.send_text("Unauthorized")
        await websocket.close(code=1008)
        LOGGER.info("Unauthorized WebSocket connection closed")


async def handle_websocket(
    websocket: WebSocket,
    wallet_id: str,
    topic: str,
    auth: AcaPyAuthVerified,
):
    await websocket.accept()

    if not auth or auth.wallet_id not in ("admin", wallet_id):
        await websocket.send_text("Unauthorized")
        await websocket.close(code=1008)
        LOGGER.info("Unauthorized WebSocket connection closed")

    try:
        # Subscribe the WebSocket connection to the wallet / topic
        await WebsocketManager.subscribe(websocket, wallet_id, topic)

        # Keep the connection open until the client disconnects
        while True:
            await asyncio.sleep(DISCONNECT_CHECK_PERIOD)
    except WebSocketDisconnect:
        LOGGER.info("WebSocket connection closed")
    except Exception as e:
        LOGGER.error("Exception caught while handling websocket: %r", e)


@router.websocket("/ws/{wallet_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    wallet_id: str,
    auth: AcaPyAuthVerified = Depends(websocket_auth),
):
    await handle_websocket(websocket, wallet_id, "", auth)


@router.websocket("/ws/{wallet_id}/{topic}")
async def websocket_endpoint_topic(
    websocket: WebSocket,
    wallet_id: str,
    topic: str,
    auth: AcaPyAuthVerified = Depends(websocket_auth),
):
    await handle_websocket(websocket, wallet_id, topic, auth)


@router.websocket("/ws/topic/{topic}")
async def websocket_endpoint_admin(
    websocket: WebSocket,
    topic: str,
    auth: AcaPyAuthVerified = Depends(websocket_auth),
):
    await handle_websocket(websocket, "", topic, auth)
