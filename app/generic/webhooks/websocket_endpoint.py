import asyncio

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from app.dependencies.auth import (
    AcaPyAuthVerified,
    get_acapy_auth,
    get_acapy_auth_verified,
)
from app.event_handling.websocket_manager import WebsocketManager
from shared.log_config import get_logger

logger = get_logger(__name__)
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
        logger.info("Unauthorized WebSocket connection closed.")


async def handle_websocket(
    websocket: WebSocket,
    wallet_id: str,
    topic: str,
    auth: AcaPyAuthVerified,
):
    bound_logger = logger.bind(body={"wallet_id": wallet_id, "topic": topic})
    bound_logger.debug("Accepting websocket")
    await websocket.accept()
    bound_logger.debug("Accepted websocket")

    if (
        not auth
        or (
            wallet_id and auth.wallet_id not in ("admin", wallet_id)
        )  # tenants can subscribe to their own wallets; admin can subscribe to any wallet
        or (
            not wallet_id and auth.wallet_id != "admin"
        )  # only admin can subscribe to topic (wallet_id == "")
    ):
        bound_logger.debug("Notifying user is unauthorized")
        await websocket.send_text("Unauthorized")
        await websocket.close(code=1008)
        bound_logger.info("Unauthorized WebSocket connection closed")

    uuid = None
    try:
        # Subscribe the WebSocket connection to the wallet / topic
        uuid = await WebsocketManager.subscribe(websocket, wallet_id, topic)

        # Keep the connection open until the client disconnects
        while True:
            await asyncio.sleep(DISCONNECT_CHECK_PERIOD)
    except WebSocketDisconnect:
        bound_logger.info("WebSocket connection closed.")
    except Exception:
        bound_logger.exception("Exception caught while handling websocket.")
    else:
        if uuid:
            await WebsocketManager.unsubscribe(uuid)


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
