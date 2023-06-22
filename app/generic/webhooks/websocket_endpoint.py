import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from app.event_handling.websocket_manager import WebsocketManager
from app.main import get_manager
from shared.dependencies.auth import AcaPyAuthVerified, acapy_auth_verified

LOGGER = logging.getLogger(__name__)
router = APIRouter()

# Singleton pattern
manager: WebsocketManager = get_manager()


async def handle_websocket(
    websocket: WebSocket,
    wallet_id: str,
    topic: str,
    auth: AcaPyAuthVerified,
):
    try:
        # Subscribe the WebSocket connection to the wallet / topic
        await manager.subscribe(websocket, wallet_id, topic)

        while True:
            data = await websocket.receive_text()
            # Forward the message to the original server
            await websocket.send_text(f"{wallet}: {data}")
    except WebSocketDisconnect:
        LOGGER.info("WebSocket connection closed")
    except Exception as e:
        LOGGER.error("Exception caught while handling websocket: %r", e)

    await handle_websocket(websocket, wallet_id, "", auth)

    await handle_websocket(websocket, wallet_id, topic, auth)


    await handle_websocket(websocket, "", topic, auth)
