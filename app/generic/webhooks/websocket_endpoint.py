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

@router.websocket("/ws/{wallet}")
async def websocket_endpoint(websocket: WebSocket, wallet: str):
    await manager.connect(websocket, wallet)
    try:
        while True:
            data = await websocket.receive_text()
            # Forward the message to the original server
            await websocket.send_text(f"{wallet}: {data}")
    except WebSocketDisconnect:
        LOGGER.info("WebSocket connection closed")
        LOGGER.error("Exception caught while handling websocket: %r", e)
