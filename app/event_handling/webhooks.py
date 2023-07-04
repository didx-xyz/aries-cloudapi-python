import asyncio
import json
from typing import Any, Awaitable, Callable, Dict, List, Optional

from fastapi import WebSocket, WebSocketDisconnect
from fastapi_websocket_pubsub import PubSubClient

from app.config.log_config import get_logger
from shared import WEBHOOK_TOPIC_ALL, WEBHOOKS_URL

logger = get_logger(__name__)


class Webhooks:
    """
    A class for managing webhook callbacks, emitting webhook events, and handling the underlying
    WebSocket communication.
    """

    _callbacks: List[Callable[[Dict[str, Any]], Awaitable[None]]] = []
    _ready = asyncio.Event()
    client: Optional[PubSubClient] = None
    sse_clients: List[WebSocket] = []

    @staticmethod
    async def register_callback(callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        """
        Register a listener function to be called when a webhook event is received.
        """
        if not Webhooks.client:
            await Webhooks.start_webhook_client()

        Webhooks._callbacks.append(callback)

    @staticmethod
    async def register_sse_client(websocket: WebSocket):
        """
        Register a WebSocket for Server-Sent Events (SSE).
        """
        Webhooks.sse_clients.append(websocket)

    @staticmethod
    async def emit(data: Dict[str, Any]):
        """
        Emit a webhook event by calling all registered listener functions with the event data.
        """
        for callback in Webhooks._callbacks:
            await callback(data)
        # todo: surely we don't need to submit data to every single callback

        # Send the event to SSE clients
        for websocket in Webhooks.sse_clients:
            await websocket.send_text(json.dumps(data))

    @staticmethod
    def unregister_callback(callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        """
        Unregister a listener function so that it will no longer be called when a webhook event is received.
        """
        logger.debug("Unregistering a callback")

        try:
            Webhooks._callbacks.remove(callback)
        except ValueError:
            # Listener not in list
            pass

    @staticmethod
    async def unregister_sse_client(websocket: WebSocket):
        """
        Unregister a WebSocket for Server-Sent Events (SSE).
        """
        try:
            Webhooks.sse_clients.remove(websocket)
        except ValueError:
            # WebSocket not in list
            pass

    @staticmethod
    async def start_webhook_client(timeout: float = 30):
        """
        Start listening for webhook events on a WebSocket connection with a specified timeout.
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
                raise WebhooksTimeout("Starting Webhooks has timed out") from e
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

    @staticmethod
    async def sse_endpoint(websocket: WebSocket):
        """
        Server-Sent Events (SSE) endpoint.
        """
        await websocket.accept()
        await Webhooks.register_sse_client(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            await Webhooks.unregister_sse_client(websocket)

    @staticmethod
    async def shutdown(timeout: float = 20):
        """
        Shutdown the Webhooks client and clear the listeners with a specified timeout.
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
            raise WebhooksTimeout("Webhooks shutdown timed out") from e


class WebhooksTimeout(Exception):
    """Exception raised when Webhooks functions time out."""


def convert_url_to_websocket(url: str) -> str:
    """
    Convert an HTTP or HTTPS URL to WebSocket (WS or WSS) URL.
    """
    if url.startswith("http"):
        return "ws" + url[4:]
    else:
        return url
