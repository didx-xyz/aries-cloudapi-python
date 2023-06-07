import asyncio
import logging
from collections import defaultdict as ddict
from contextlib import asynccontextmanager
from typing import Any, Generator, Tuple

from webhooks.dependencies.service import Service

LOGGER = logging.getLogger(__name__)


class SseManager:
    """
    Class to manage Server-Sent Events (SSE).
    """

    def __init__(self, service: Service, max_queue_size=20):
        self.service = service
        self.locks = ddict(lambda: ddict(asyncio.Lock))  # Concurrency per wallet/topic
        self.max = max_queue_size

        # The following nested defaultdict stores events per wallet_id, per topic
        self.fifo_cache = ddict(lambda: ddict(lambda: asyncio.Queue(self.max)))
        self.lifo_cache = ddict(lambda: ddict(lambda: asyncio.LifoQueue(self.max)))
        # Last In First Out Queue is to be used for consumption, so that newest events are yielded first
        # FIFO Queue maintains order of events and is used to repopulate LIFO queue after consumption

    @asynccontextmanager
    async def sse_event_stream(
        self, wallet: str, topic: str
    ) -> Generator[asyncio.LifoQueue, Any, None]:
        """
        Create a SSE stream of events for a wallet_id on a specific topic

        Args:
            wallet: The ID of the wallet subscribing to the topic.
            topic: The topic for which to create the event stream.
        """
        async with self.locks[wallet][topic]:
            lifo_queue = self.lifo_cache[wallet][topic]

        try:
            yield lifo_queue  # Will include any new events added to lifo_queue after generator starts
        finally:
            async with self.locks[wallet][topic]:
                # LIFO cache has been consumed; repopulate with events from FIFO cache:
                lifo_queue, fifo_queue = await _copy_queue(
                    self.fifo_cache[wallet][topic], self.max
                )
                self.fifo_cache[wallet][topic] = fifo_queue
                self.lifo_cache[wallet][topic] = lifo_queue

    async def enqueue_sse_event(self, event: str, wallet: str, topic: str) -> None:
        """
        Enqueue a SSE event to be sent to a specific wallet for a specific topic.

        Args:
            event: The event to enqueue.
            wallet: The ID of the wallet to which to enqueue the event.
            topic: The topic to which to enqueue the event.
        """
        LOGGER.debug(
            "Enqueueing event for wallet '%s': %s",
            wallet,
            event,
        )

        async with self.locks[wallet][topic]:
            # Check if queue is full and make room before adding events
            if self.lifo_cache[wallet][topic].full():
                await self.lifo_cache[wallet][topic].get()

            if self.fifo_cache[wallet][topic].full():
                await self.fifo_cache[wallet][topic].get()

            await self.lifo_cache[wallet][topic].put(event)
            await self.fifo_cache[wallet][topic].put(event)


async def _copy_queue(
    queue: asyncio.Queue, maxsize: int
) -> Tuple[asyncio.LifoQueue, asyncio.Queue]:
    # Consuming a queue removes its content. Therefore, we create two new queues to copy one
    lifo_queue, fifo_queue = asyncio.LifoQueue(maxsize), asyncio.Queue(maxsize)
    while not queue.empty():
        item = await queue.get()
        await lifo_queue.put(item)
        await fifo_queue.put(item)

    return lifo_queue, fifo_queue
