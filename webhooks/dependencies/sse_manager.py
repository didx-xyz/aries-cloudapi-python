import asyncio
import logging
import time
from collections import defaultdict as ddict
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Generator, Tuple

from shared import TopicItem
from webhooks.dependencies.service import Service

LOGGER = logging.getLogger(__name__)

MAX_EVENT_AGE_SECONDS = 5
MAX_QUEUE_SIZE = 50


class SseManager:
    """
    Class to manage Server-Sent Events (SSE).
    """

    def __init__(self, service: Service, max_queue_size=MAX_QUEUE_SIZE):
        self.service = service
        self.max = max_queue_size

        # Concurrency per wallet/topic
        self.cache_locks = ddict(lambda: ddict(asyncio.Lock))

        # The following nested defaultdict stores events per wallet_id, per topic
        self.fifo_cache = ddict(lambda: ddict(lambda: asyncio.Queue(self.max)))
        self.lifo_cache = ddict(lambda: ddict(lambda: asyncio.LifoQueue(self.max)))
        # Last In First Out Queue is to be used for consumption, so that newest events are yielded first
        # FIFO Queue maintains order of events and is used to repopulate LIFO queue after consumption

        # Define incoming events queue, to decouple the process of receiving events,
        # from the process of storing them in the per-wallet queues
        self.incoming_events = asyncio.Queue()

        # Start a background task to process incoming events
        self._incoming_events_task = asyncio.create_task(
            self._process_incoming_events()
        )

        # To handles queues for incoming client request
        self.client_queues = ddict(asyncio.Queue)
        self.client_locks = ddict(asyncio.Lock)

    async def enqueue_sse_event(
        self, event: TopicItem, wallet: str, topic: str
    ) -> None:
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

        # Add the event to the incoming events queue, with timestamp
        await self.incoming_events.put((event, wallet, topic, time.time()))

    async def _process_incoming_events(self):
        while True:
            # Wait for an event to be added to the incoming events queue
            event, wallet, topic, timestamp = await self.incoming_events.get()

            # Process the event into the per-wallet queues
            async with self.cache_locks[wallet][topic]:
                # Check if queue is full and make room before adding events
                if self.fifo_cache[wallet][topic].full():
                    await self.fifo_cache[wallet][topic].get()

                    # cannot pop from lifo queue; rebuild from fifo queue
                    lifo_queue, fifo_queue = await _copy_queue(
                        self.fifo_cache[wallet][topic], self.max
                    )
                    self.fifo_cache[wallet][topic] = fifo_queue
                    self.lifo_cache[wallet][topic] = lifo_queue

                timestamped_event: Tuple(float, TopicItem) = (timestamp, event)
                await self.lifo_cache[wallet][topic].put(timestamped_event)
                await self.fifo_cache[wallet][topic].put(timestamped_event)

    @asynccontextmanager
    async def sse_event_stream(
        self, wallet: str, topic: str, duration: int = 0
    ) -> Generator[AsyncGenerator[TopicItem, Any], Any, None]:
        """
        Create a SSE stream of events for a wallet_id on a specific topic

        Args:
            wallet: The ID of the wallet subscribing to the topic.
            topic: The topic for which to create the event stream.
            duration: Timeout duration in seconds. 0 means no timeout.
        """
        async with self.client_locks[(wallet, topic)]:
            client_queue = self.client_queues[(wallet, topic)]
            self._client_last_accessed[(wallet, topic)] = datetime.now()

        populate_task = asyncio.create_task(
            self._populate_client_queue(wallet, topic, client_queue)
        )

            start_time = time.time()
            while True:
                try:
                    timestamp, event = await asyncio.wait_for(
                        lifo_queue.get(), timeout=1
                    )
                    if time.time() - timestamp > MAX_EVENT_AGE_SECONDS:
                        continue
                    yield event
                except asyncio.TimeoutError:
                    if duration > 0 and time.time() - start_time > duration:
                        LOGGER.info("\nSSE Event Stream: closing with timeout error")
                        break

        try:
            yield event_generator()
        finally:
            populate_task.cancel()
            async with self.cache_locks[wallet][topic]:
                # LIFO cache has been consumed; repopulate with events from FIFO cache:
                lifo_queue, fifo_queue = await _copy_queue(
                    self.fifo_cache[wallet][topic], self.max
                )
                self.fifo_cache[wallet][topic] = fifo_queue
                self.lifo_cache[wallet][topic] = lifo_queue

    async def _populate_client_queue(
        self, wallet: str, topic: str, client_queue: asyncio.Queue
    ):
        while True:
            if topic == WEBHOOK_TOPIC_ALL:
                for topic_key in self.lifo_cache[wallet].keys():
                    async with self.cache_locks[wallet][topic_key]:
                        lifo_queue = self.lifo_cache[wallet][topic_key]
                        try:
                            timestamp, event = lifo_queue.get_nowait()
                            if time.time() - timestamp <= MAX_EVENT_AGE_SECONDS:
                                async with self.client_locks[(wallet, topic)]:
                                    await client_queue.put(event)
                                    self._client_last_accessed[
                                        (wallet, topic)
                                    ] = datetime.now()
                            # We've consumed from the lifo_queue, so we should repopulate it:
                            lifo_queue, fifo_queue = await _copy_queue(
                                self.fifo_cache[wallet][topic_key], self.max
                            )
                            self.fifo_cache[wallet][topic_key] = fifo_queue
                            self.lifo_cache[wallet][topic_key] = lifo_queue
                        except asyncio.QueueEmpty:
                            # No event on lifo_queue, so we can continue
                            pass
            else:
                async with self.cache_locks[wallet][topic]:
                    lifo_queue = self.lifo_cache[wallet][topic]
                    try:
                        timestamp, event = lifo_queue.get_nowait()
                        if time.time() - timestamp <= MAX_EVENT_AGE_SECONDS:
                            async with self.client_locks[(wallet, topic)]:
                                await client_queue.put(event)
                                self._client_last_accessed[
                                    (wallet, topic)
                                ] = datetime.now()
                        # We've consumed from the lifo_queue, so we should repopulate it:
                        lifo_queue, fifo_queue = await _copy_queue(
                            self.fifo_cache[wallet][topic], self.max
                        )
                        self.fifo_cache[wallet][topic] = fifo_queue
                        self.lifo_cache[wallet][topic] = lifo_queue
                    except asyncio.QueueEmpty:
                        # No event on lifo_queue, so we can continue
                        pass

async def _copy_queue(
    queue: asyncio.Queue, maxsize: int
) -> Tuple[asyncio.LifoQueue, asyncio.Queue]:
    # Consuming a queue removes its content. Therefore, we create two new queues to copy one
    lifo_queue, fifo_queue = asyncio.LifoQueue(maxsize), asyncio.Queue(maxsize)
    while True:
        try:
            timestamp, item = queue.get_nowait()
            if (
                time.time() - timestamp <= MAX_EVENT_AGE_SECONDS
            ):  # only copy events that are less than a minute old
                await lifo_queue.put((timestamp, item))
                await fifo_queue.put((timestamp, item))
        except asyncio.QueueEmpty:
            break

    return lifo_queue, fifo_queue
