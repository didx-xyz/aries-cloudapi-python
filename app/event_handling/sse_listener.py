import asyncio
import json
import logging

import httpx

from shared import WEBHOOKS_URL

LOGGER = logging.getLogger(__name__)
base_url = f"{WEBHOOKS_URL}/sse"


class SseListener:
    """
    A class for listening to SSE events filtered by topic, wallet_id, a field, the field_id, and desired_state.
    Events that match the given parameters are processed by a callback function.
    """

    def __init__(
        self,
        wallet_id: str,
        topic: str,
    ):
        self.wallet_id = wallet_id
        self.topic = topic

    async def wait_for_state(self, desired_state, duration: int = 60):
        """
        Start listening for SSE events. When an event is received that matches the specified parameters.
        """
        url = f"{base_url}/{self.wallet_id}/{self.topic}/{desired_state}"

        timeout = httpx.Timeout(duration)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("GET", url) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        return data["payload"]
                    elif line == "" or line.startswith(": ping"):
                        pass  # ignore newlines and pings
                    else:
                        LOGGER.warning(f"Unexpected SSE line: {line}")

        raise SseListenerTimeout("Event with request state was not returned by server")

    async def wait_for_event(self, field, field_id, desired_state, duration: int = 60):
        """
        Start listening for SSE events. When an event is received that matches the specified parameters.
        """
        url = f"{base_url}/{self.wallet_id}/{self.topic}/{field}/{field_id}/{desired_state}"

        timeout = httpx.Timeout(duration)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("GET", url) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        return data["payload"]
                    elif line == "" or line.startswith(": ping"):
                        pass  # ignore newlines and pings
                    else:
                        LOGGER.warning(f"Unexpected SSE line: {line}")

        raise SseListenerTimeout("Requested filtered event was not returned by server")


class SseListenerTimeout(Exception):
    """Exception raised when the Listener times out waiting for a matching event."""
