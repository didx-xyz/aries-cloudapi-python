import asyncio
import json
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from fastapi_websocket_pubsub import PubSubClient

from app.constants import WEBHOOKS_URL
from shared_models import WEBHOOK_TOPIC_ALL, CloudApiTopics

logger = logging.getLogger(__name__)


class Webhooks:
    """
    A class for managing webhook listeners, emitting webhook events, and handling the underlying
    WebSocket communication.
    """
    _listeners: List[Callable[[Dict[str, Any]], Awaitable[None]]] = []
    client: Optional[PubSubClient] = None

    # TODO: add timeout to listening to webhooks
    @staticmethod
        """
        Register a listener function to be called when a webhook event is received.
        """
        if not Webhooks.client:
            await Webhooks.listen_webhooks()
        Webhooks._listeners.append(f)

    @staticmethod
    async def emit(data: Dict[str, Any]):
        """
        Emit a webhook event by calling all registered listener functions with the event data.
        """

    @staticmethod
        """
        Unregister a listener function so that it will no longer be called when a webhook event is received.
        """
        try:
            Webhooks._listeners.remove(f)
        except ValueError:
            # Listener not in list
            pass

    @staticmethod
        """
        Start listening for webhook events on a WebSocket connection with a specified timeout.
        """
        async def wait_for_ready():
            Webhooks.client = PubSubClient(
                [WEBHOOK_TOPIC_ALL], callback=Webhooks._on_webhook
            )

            ws_url = WEBHOOKS_URL
            if ws_url.startswith("http"):
                ws_url = "ws" + ws_url[4:]

            Webhooks.client.start_client(ws_url + "/pubsub")
            await Webhooks.client.wait_until_ready()

        try:
            await asyncio.wait_for(wait_for_ready(), timeout=30)
        except asyncio.TimeoutError:
            if Webhooks.client:
                await Webhooks.client.disconnect()
            raise WebhooksShutdownTimeout(
                f"Webhooks shutdown timed out ({timeout}s)")

    @staticmethod
    async def _on_webhook(data: str, topic: str):
        """
        Internal callback function for handling received webhook events.
        """
        await Webhooks.emit(json.loads(data))

    @staticmethod
        """
        Shutdown the Webhooks client and clear the listeners with a specified timeout.
        """
        async def wait_for_shutdown():
            if Webhooks.client:
                await Webhooks.client.disconnect()
                Webhooks.client = None

            Webhooks._listeners = []

        try:
            await asyncio.wait_for(wait_for_shutdown(), timeout=20)
        except asyncio.TimeoutError:
            raise WebhooksShutdownTimeout(
                f"Webhooks shutdown timed out ({timeout}s)")


async def start_listener(*, topic: CloudApiTopics, wallet_id: str):
    queue = asyncio.Queue()

    async def on_webhook(data: Dict[str, Any]):
        # Do not flood the queue with unnecessary webhook events. We require topic and wallet_id
        if data["topic"] == topic and data["wallet_id"] == wallet_id:
            await queue.put(data)

    async def wait_for_event(filter_map: Dict[str, Any]) -> Dict[str, Any]:
        while True:
            # Wait for item from the queue
            item = await queue.get()

            payload = item["payload"]

            # Check if there is a match based on filters
            match = all(
                payload.get(filter_key, None) == filter_value
                for filter_key, filter_value in filter_map.items()
            )

            if match:
                return payload

    async def wait_for_event_with_timeout(
        *, filter_map: Dict[str, Any], timeout: float = 180
    ):
        try:
            payload = await asyncio.wait_for(
                wait_for_event(filter_map), timeout=timeout
            )
            Webhooks.off(on_webhook)
            return payload
        except Exception:
            raise
        finally:
            # Always unsubscribe
            Webhooks.off(on_webhook)
            raise e from e

    async def stop_listener():
        Webhooks.off(on_webhook)

    # Subscribe to webhook events and put them in a queue
    await Webhooks.on(on_webhook)

    return wait_for_event_with_timeout, stop_listener


class WebhooksShutdownTimeout(Exception):
    """Exception raised when the Webhooks shutdown times out."""
    pass
