import asyncio
import logging
from typing import Optional

from fastapi import WebSocket
from fastapi_websocket_pubsub import PubSubClient

from shared import WEBHOOKS_URL

logger = logging.getLogger(__name__)


    """
    """

    def __init__(self):
        self.client: Optional[PubSubClient] = None
        self._ready = asyncio.Event()

        """
        """

            await websocket.send_text(data)


    async def start_pubsub_client(self, timeout: float = 30):
        """
        Start listening for webhook events on the Webhooks pubsub endpoint with a specified timeout.
        """

        async def ensure_connection_ready():
            """
            Ensure the connection is established before proceeding
            """
            websocket_url = convert_url_to_websocket(WEBHOOKS_URL)
            self.client.start_client(websocket_url + "/pubsub")
            await self.client.wait_until_ready()

        if not self.client:
            try:
                await asyncio.wait_for(ensure_connection_ready(), timeout=timeout)
            except asyncio.TimeoutError as e:
                logger.warning(
                )
                await self.shutdown()
        else:
            logger.debug(
                "Requested to start Webhook client when it's already started. Ignoring."
            )

    async def shutdown(self, timeout: float = 20):
        """
        Shutdown the Websocket client and clear the connections with a specified timeout.
        """
        logger.debug("Shutting down Websocket client")

        async def wait_for_shutdown():
            if self.client and await self._ready.wait():
                await self.client.disconnect()

            self.client = None
            self._ready = asyncio.Event()

        try:
            await asyncio.wait_for(wait_for_shutdown(), timeout=timeout)
        except asyncio.TimeoutError as e:


class WebsocketTimeout(Exception):


def convert_url_to_websocket(url: str) -> str:
    """
    Convert an HTTP or HTTPS URL to WebSocket (WS or WSS) URL.
    """
    if url.startswith("http"):
        return "ws" + url[4:]
    else:
        return url
