import asyncio
from typing import Optional

from fastapi import WebSocket
from fastapi_websocket_pubsub import PubSubClient

from shared import WEBHOOKS_URL
from shared.log_config import get_logger

logger = get_logger(__name__)


class WebsocketManager:
    """
    A class for managing websocket connections and establishing PubSub callbacks
    """

    _client: Optional[PubSubClient] = None

    @staticmethod
    async def subscribe(websocket: WebSocket, wallet_id: str = "", topic: str = ""):
        """
        Subscribe a websocket connection to a specific topic.
        """
        if not WebsocketManager._client:
            await WebsocketManager.start_pubsub_client()

        async def callback(data: str, topic: str):
            """
            Callback function for handling received webhook events.
            Note: PubSubClient expects a topic argument in callback
            """
            await websocket.send_text(data)

        if wallet_id and topic:
            subscribed_topic = f"{topic}-{wallet_id}"
        elif wallet_id:
            subscribed_topic = wallet_id
        elif topic:
            subscribed_topic = topic
        else:
            logger.error("Subscribe requires `topic` or `wallet_id` in request.")
            return

        WebsocketManager._client.subscribe(subscribed_topic, callback)

    @staticmethod
    async def start_pubsub_client(timeout: float = 10):
        """
        Start listening for webhook events on the Webhooks pubsub endpoint with a specified timeout.
        """

        async def ensure_connection_ready():
            """
            Ensure the connection is established before proceeding
            """
            WebsocketManager._client = PubSubClient()
            websocket_url = convert_url_to_websocket(WEBHOOKS_URL)
            WebsocketManager._client.start_client(websocket_url + "/pubsub")
            await WebsocketManager._client.wait_until_ready()

        if not WebsocketManager._client:
            try:
                logger.debug("Starting PubSubClient for Websocket Manager")
                await asyncio.wait_for(ensure_connection_ready(), timeout=timeout)
            except asyncio.TimeoutError as e:
                logger.warning(
                    "Starting Websocket PubSubClient has timed out after {}s.", timeout
                )
                await WebsocketManager.shutdown()
                raise WebsocketTimeout(
                    "Starting PubSubClient for Websocket Manager has timed out."
                ) from e
        else:
            logger.debug(
                "Requested to start Webhook client when it's already started. Ignoring."
            )

    @staticmethod
    async def shutdown(timeout: float = 10):
        """
        Shutdown the Websocket client and clear the connections with a specified timeout.
        """
        logger.debug("Shutting down Websocket client")

        async def wait_for_shutdown():
            if WebsocketManager._client:
                await WebsocketManager._client.disconnect()

            WebsocketManager._client = None

        try:
            await asyncio.wait_for(wait_for_shutdown(), timeout=timeout)
        except asyncio.TimeoutError as e:
            logger.warning(
                "Shutting down Websocket Manager has timed out after {}s.", timeout
            )
            raise WebsocketTimeout("Websocket Manager shutdown timed out.") from e


class WebsocketTimeout(Exception):
    """Exception raised when Websocket functions time out."""


def convert_url_to_websocket(url: str) -> str:
    """
    Convert an HTTP or HTTPS URL to WebSocket (WS or WSS) URL.
    """
    if url.startswith("http"):
        return "ws" + url[4:]
    else:
        return url
