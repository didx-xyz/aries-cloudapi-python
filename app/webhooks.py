import asyncio
import json
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

from fastapi_websocket_pubsub import PubSubClient

from app.constants import WEBHOOKS_URL
from shared_models import WEBHOOK_TOPIC_ALL

logger = logging.getLogger(__name__)


def convert_url_to_ws(url: str) -> str:
    """
    Convert an HTTP or HTTPS URL to WebSocket (WS or WSS) URL.
    """
    if url.startswith("http"):
        return "ws" + url[4:]
    else:
        return url


class Webhooks:
    """
    A class for managing webhook callbacks, emitting webhook events, and handling the underlying
    WebSocket communication.
    """
    _callbacks: List[Callable[[Dict[str, Any]], Awaitable[None]]] = []
    client: Optional[PubSubClient] = None

    @staticmethod
    async def register_callback(callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        """
        Register a listener function to be called when a webhook event is received.
        """
        if not Webhooks.client:
            await Webhooks.start_webhook_client()

        Webhooks._callbacks.append(callback)

    @staticmethod
    async def emit(data: Dict[str, Any]):
        """
        Emit a webhook event by calling all registered listener functions with the event data.
        """
        for callback in Webhooks._callbacks:  # todo: surely we don't need to submit data to every single callback
            await callback(data)

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

            ws_url = convert_url_to_ws(WEBHOOKS_URL)

            Webhooks.client.start_client(ws_url + "/pubsub")
            await Webhooks.client.wait_until_ready()

        if not Webhooks.client:
            try:
                logger.debug("Starting Webhooks client")
                await asyncio.wait_for(ensure_connection_ready(), timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning(
                    f"Starting Webhooks client has timed out after {timeout}s")
                await Webhooks.shutdown()
                raise WebhooksTimeout(f"Starting Webhooks has timed out")
        else:
            logger.debug(
                f"Tried to start Webhook client when it's already started. Ignoring.")

    @staticmethod
    async def _handle_webhook(data: str, topic: str):
        """
        Internal callback function for handling received webhook events.
        """
        logger.debug(f"Handling webhook for topic: {topic} - emit {data}")

        await Webhooks.emit(json.loads(data))

    @staticmethod
    async def shutdown(timeout: float = 20):
        """
        Shutdown the Webhooks client and clear the listeners with a specified timeout.
        """
        logger.debug("Shutting down Webhooks client")

        async def wait_for_shutdown():
            if Webhooks.client:
                await Webhooks.client.disconnect()
                Webhooks.client = None

            Webhooks._callbacks = []

        try:
            await asyncio.wait_for(wait_for_shutdown(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(
                f"Shutting down Webhooks has timed out after {timeout}s")
            raise WebhooksTimeout(f"Webhooks shutdown timed out")


class WebhooksTimeout(Exception):
    """Exception raised when Webhooks functions time out."""
    pass
