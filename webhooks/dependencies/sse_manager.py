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

    def __init__(self, service: Service, max_queue_size=20):
        self.service = service
        self.locks = ddict(asyncio.Lock)  # Concurrency management per wallet
        self.max = max_queue_size

        # The following nested defaultdict stores events per wallet_id, per topic
        self.events = ddict(lambda: ddict(lambda: asyncio.Queue(maxsize=self.max)))
        # A copy is maintained so that events consumed from the above queue can be re-added. Alternatively,
        # consumed events can be individually re-added. This is so repeated requests can receive same events.
        self.cache = ddict(lambda: ddict(lambda: asyncio.Queue(maxsize=self.max)))

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

        try:
            yield queue
        finally:
            # refill the queue from the copy
            async with self.locks[wallet]:
                queue1, queue2 = await _copy_queue(self.cache[wallet][topic], self.max)
                self.clients[wallet][topic] = queue1
                self.cache[wallet][topic] = queue2

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

        async with self.locks[wallet]:
            await self.clients[wallet][topic].put(event)
            await self.cache[wallet][topic].put(event)
