import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Union
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketTestSession
from starlette.websockets import WebSocketDisconnect

from app.dependencies.auth import AcaPyAuth, AcaPyAuthVerified
from app.event_handling.websocket_manager import WebsocketManager
from app.generic.webhooks.websocket_endpoint import router as websocket_router

logger = logging.getLogger(__name__)

app = FastAPI()
app.include_router(websocket_router)

client = TestClient(app)


def headers(auth: Union[AcaPyAuth, AcaPyAuthVerified]):
    h = {"x-api-key": f"{auth.role.role_name}.{auth.token}"}
    return h


@pytest.fixture
def mock_websocket_manager():
    with patch.object(
        WebsocketManager, "subscribe", return_value=None
    ) as mock_subscribe:
        yield mock_subscribe


def receive_data(websocket):
    return websocket.receive_text()


@pytest.mark.anyio
@pytest.mark.skip("Work in progress")
async def test_websocket_endpoint(mock_admin_auth, mock_websocket_manager):
    with client.websocket_connect(
        "/ws/admin", headers=headers(mock_admin_auth)
    ) as websocket:
        try:
            websocket: WebSocketTestSession = websocket
            logger.info("send_text")
            websocket.send_text("Hello, WebSocket!")
            logger.info("receive_text")

            # Use asyncio.wait_for to timeout if no response is received within 5 seconds
            with ThreadPoolExecutor() as pool:
                data_future = pool.submit(receive_data, websocket)
                data = await asyncio.wait_for(
                    asyncio.wrap_future(data_future), timeout=5
                )

            logger.info("received text")
            assert data == "Hello, WebSocket!"  # change the assertion as per your logic
            assert mock_websocket_manager.called
        except WebSocketDisconnect:
            assert False, "The websocket connection was closed prematurely"


@pytest.mark.anyio
@pytest.mark.skip("Work in progress")
def test_websocket_endpoint_topic(mock_tenant_auth, mock_websocket_manager):
    tenant_wallet_id = mock_tenant_auth.wallet_id

    with client.websocket_connect(
        f"/ws/{tenant_wallet_id}/test_topic", headers=headers(mock_tenant_auth)
    ) as websocket:
        try:
            websocket.send_text("Hello, WebSocket!")
            data = websocket.receive_text()
            assert data == "Hello, WebSocket!"  # change the assertion as per your logic
            assert mock_websocket_manager.called
        except WebSocketDisconnect:
            assert False, "The websocket connection was closed prematurely"


@pytest.mark.anyio
@pytest.mark.skip("Work in progress")
def test_websocket_endpoint_admin(mock_admin_auth, mock_websocket_manager):
    with client.websocket_connect(
        "/ws/topic/test_topic", headers=headers(mock_admin_auth)
    ) as websocket:
        try:
            websocket.send_text("Hello, WebSocket!")
            data = websocket.receive_text()
            assert data == "Hello, WebSocket!"  # change the assertion as per your logic
            assert mock_websocket_manager.called
        except WebSocketDisconnect:
            assert False, "The websocket connection was closed prematurely"
