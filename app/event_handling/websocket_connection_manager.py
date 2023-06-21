import asyncio
import json
import logging
from typing import Dict, Optional

from fastapi import WebSocket
from fastapi_websocket_pubsub import PubSubClient

from shared import WEBHOOK_TOPIC_ALL, WEBHOOKS_URL

logger = logging.getLogger(__name__)


class WebsocketConnectionManager:
    """
    A class for managing websocket connections, emitting websocket events, and handling the underlying
    WebSocket communication.
    """

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.client: Optional[PubSubClient] = None
        self._ready = asyncio.Event()

    async def connect(self, websocket: WebSocket, wallet_id: str):
        """
        Connect a new websocket connection.
        """
        await websocket.accept()
        self.active_connections[wallet_id] = websocket

    async def disconnect(self, wallet_id: str):
        """
        Disconnect a websocket connection.
        """
        websocket = self.active_connections.pop(wallet_id, None)
        if websocket:
            await websocket.close()

    async def send(self, wallet_id: str, data: str):
        """
        Send a message to a specific websocket connection.
        """
        websocket = self.active_connections.get(wallet_id)
        if websocket:
            await websocket.send_text(data)

    async def subscribe(self, wallet_id: str, topic: str):
        """
        Subscribe a websocket connection to a specific topic.
        """
        if not self.client:
            await self.start_pubsub_client()

        self.client.subscribe(topic)

    async def start_pubsub_client(self, timeout: float = 30):
        """
        Start listening for webhook events on the Webhooks pubsub endpoint with a specified timeout.
        """

        async def ensure_connection_ready():
            """
            Ensure the connection is established before proceeding
            """
            self.client = PubSubClient(
                [WEBHOOK_TOPIC_ALL], callback=self._handle_webhook
            )

            websocket_url = convert_url_to_websocket(WEBHOOKS_URL)

            self.client.start_client(websocket_url + "/pubsub")
            await self.client.wait_until_ready()

        if not self.client:
            try:
                logger.debug("Starting Webhooks client")
                await asyncio.wait_for(ensure_connection_ready(), timeout=timeout)
            except asyncio.TimeoutError as e:
                logger.warning(
                    "Starting Webhooks client has timed out after %ss", timeout
                )
                await self.shutdown()
                raise WebsocketTimeout("Starting Webhooks has timed out") from e
        else:
            logger.debug(
                "Requested to start Webhook client when it's already started. Ignoring."
            )

    async def _handle_webhook(self, data: str, topic: str):
        """
        Internal callback function for handling received webhook events.
        """
        # todo: topic isn't used. should only emit to relevant topic/callback pairs
        await self.send(json.loads(data))

    async def shutdown(self, timeout: float = 20):
        """
        Shutdown the Websocket client and clear the connections with a specified timeout.
        """
        logger.debug("Shutting down Webhooks client")

        async def wait_for_shutdown():
            if self.client and await self._ready.wait():
                await self.client.disconnect()

            self.client = None
            self._ready = asyncio.Event()
            self.active_connections = {}

        try:
            await asyncio.wait_for(wait_for_shutdown(), timeout=timeout)
        except asyncio.TimeoutError as e:
            logger.warning("Shutting down Webhooks has timed out after %ss", timeout)
            raise WebsocketTimeout("Webhooks shutdown timed out") from e


class WebsocketTimeout(Exception):
    """Exception raised when Webhooks functions time out."""


def convert_url_to_websocket(url: str) -> str:
    """
    Convert an HTTP or HTTPS URL to WebSocket (WS or WSS) URL.
    """
    if url.startswith("http"):
        return "ws" + url[4:]
    else:
        return url
