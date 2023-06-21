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

    @staticmethod
    async def register_callback(callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        """
        Connect a new websocket connection.
        """
        if not Webhooks.client:
            await Webhooks.start_webhook_client()

    async def disconnect(self, wallet_id: str):
        """
        Disconnect a websocket connection.
        """

    async def send(self, wallet_id: str, data: str):
        """
        Send a message to a specific websocket connection.
        """
        for callback in Webhooks._callbacks:
            await callback(data)
        # todo: surely we don't need to submit data to every single callback

    async def subscribe(self, wallet_id: str, topic: str):
        """
        Subscribe a websocket connection to a specific topic.
        """
        logger.debug("Unregistering a callback")

        try:
            Webhooks._callbacks.remove(callback)
        except ValueError:
            # Listener not in list
            pass

    async def start_pubsub_client(self, timeout: float = 30):
        """
        Start listening for webhook events on the Webhooks pubsub endpoint with a specified timeout.
        """

        async def ensure_connection_ready():
            """
            Ensure the connection is established before proceeding
            """
            Webhooks.client = PubSubClient(
                [WEBHOOK_TOPIC_ALL], callback=Webhooks._handle_webhook
            )

            websocket_url = convert_url_to_websocket(WEBHOOKS_URL)

            Webhooks.client.start_client(websocket_url + "/pubsub")
            await Webhooks.wait_until_client_ready()

        if not Webhooks.client:
            try:
                logger.debug("Starting Webhooks client")
                await asyncio.wait_for(ensure_connection_ready(), timeout=timeout)
            except asyncio.TimeoutError as e:
                logger.warning(
                    "Starting Webhooks client has timed out after %ss", timeout
                )
                await Webhooks.shutdown()
                raise WebsocketTimeout("Starting Webhooks has timed out") from e
        else:
            logger.debug(
                "Requested to start Webhook client when it's already started. Ignoring."
            )

    @staticmethod
    async def wait_until_client_ready():
        if Webhooks.client:
            await Webhooks.client.wait_until_ready()
            Webhooks._ready.set()

    @staticmethod
    async def _handle_webhook(data: str, topic: str):
        """
        Internal callback function for handling received webhook events.
        """
        # todo: topic isn't used. should only emit to relevant topic/callback pairs
        await Webhooks.emit(json.loads(data))

    async def shutdown(self, timeout: float = 20):
        """
        Shutdown the Websocket client and clear the connections with a specified timeout.
        """
        logger.debug("Shutting down Webhooks client")

        async def wait_for_shutdown():
            if Webhooks.client and await Webhooks._ready.wait():
                await Webhooks.client.disconnect()

            Webhooks.client = None
            Webhooks._ready = asyncio.Event()
            Webhooks._callbacks = []

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
