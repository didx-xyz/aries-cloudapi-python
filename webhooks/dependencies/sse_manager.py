import asyncio
import logging
from collections import defaultdict as ddict
from contextlib import asynccontextmanager
from typing import Any, Generator

from webhooks.dependencies.service import Service

LOGGER = logging.getLogger(__name__)


class SseManager:
    """
    Class to manage Server-Sent Events (SSE).
    """

    def __init__(self, service: Service):
        self.service = service
        self.clients = ddict(lambda: ddict(lambda: asyncio.Queue(maxsize=200)))
        self.locks = ddict(asyncio.Lock)  # Concurrency management per wallet

    @asynccontextmanager
    async def sse_event_stream(
        self, wallet_id: str, topic: str
    ) -> Generator[asyncio.Queue, Any, None]:
        """
        Create a SSE event stream for a topic using a provided service.

        Args:
            wallet_id: The ID of the wallet subscribing to the topic.
            topic: The topic for which to create the event stream.
        """
        async with self.locks[wallet_id]:
            queue = self.clients[wallet_id][topic]

        yield queue

    async def enqueue_sse_event(self, event: str, wallet_id: str, topic: str) -> None:
        """
        Enqueue a SSE event to be sent to a specific wallet for a specific topic.

        This function puts the event into the queue of the respective client.

        Args:
            event: The event to enqueue.
            wallet_id: The ID of the wallet to which to enqueue the event.
            topic: The topic to which to enqueue the event.
        """
        LOGGER.debug(
            "Enqueueing event for wallet '%s' with topic '%s': %s",
            wallet_id,
            topic,
            event,
        )

        async with self.locks[wallet_id]:
            await self.clients[wallet_id][topic].put(event)
