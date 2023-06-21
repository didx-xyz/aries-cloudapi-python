from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.event_handling.websocket_connection_manager import WebsocketConnectionManager

router = APIRouter()
manager = WebsocketConnectionManager()


@router.websocket("/ws/{wallet}")
async def websocket_endpoint(websocket: WebSocket, wallet: str):
    await manager.connect(websocket, wallet)
    try:
        while True:
            data = await websocket.receive_text()
            # Forward the message to the original server
            await websocket.send_text(f"{wallet}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket, wallet)
