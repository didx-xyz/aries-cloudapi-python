from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict as ddict
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Tuple
from uuid import UUID

from shared import TopicItem
from shared.models.topics import WEBHOOK_TOPIC_ALL
from webhooks.dependencies.service import Service

LOGGER = logging.getLogger(__name__)

MAX_EVENT_AGE_SECONDS = 5
MAX_QUEUE_SIZE = 50
QUEUE_CLEANUP_PERIOD = 60
CLIENT_QUEUE_POLL_PERIOD = 0.1


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

        # To clean up queues that are no longer used
        self._cache_last_accessed = ddict(lambda: ddict(datetime.now))
        self._client_last_accessed = ddict(datetime.now)
        self._cleanup_task = asyncio.create_task(self._cleanup_queues())

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
                    LOGGER.warning(
                        "SSE Manager: fifo_cache is full for wallet %s and topic %s with max queue length %s",
                        wallet,
                        topic,
                        self.max,
                    )

                    await self.fifo_cache[wallet][topic].get()

                    # cannot pop from lifo queue; rebuild from fifo queue
                    lifo_queue, fifo_queue = await _copy_queue(
                        self.fifo_cache[wallet][topic], self.max
                    )
                    self.fifo_cache[wallet][topic] = fifo_queue
                    self.lifo_cache[wallet][topic] = lifo_queue

                timestamped_event: Tuple(float, TopicItem) = (timestamp, event)
                LOGGER.debug(
                    "Putting event on cache for wallet %s, topic %s: %s",
                    wallet,
                    topic,
                    event,
                )
                await self.lifo_cache[wallet][topic].put(timestamped_event)
                await self.fifo_cache[wallet][topic].put(timestamped_event)

    async def sse_event_stream(
        self, wallet: str, topic: str, stop_event: asyncio.Event, duration: int = 0
    ) -> EventGeneratorWrapper:
        """
        Create a SSE stream of events for a wallet_id on a specific topic

        Args:
            wallet: The ID of the wallet subscribing to the topic.
            topic: The topic for which to create the event stream.
            duration: Timeout duration in seconds. 0 means no timeout.
        """
        async with self.client_locks[client_id]:
            client_queue = self.client_queues[client_id]
            self._client_last_accessed[client_id] = datetime.now()

        populate_task = asyncio.create_task(
            self._populate_client_queue(wallet, topic, client_queue)
        )

        async def event_generator() -> AsyncGenerator[TopicItem, Any]:
            LOGGER.debug("SSE Manager: Starting event_generator")
            end_time = time.time() + duration if duration > 0 else None
            remaining_time = None
            while not stop_event.is_set():
                try:
                    if end_time:
                        remaining_time = end_time - time.time()
                        if remaining_time <= 0:
                            LOGGER.debug("Event generator timeout: remaining_time < 0")
                            stop_event.set()
                            break
                    event = await asyncio.wait_for(
                        client_queue.get(), timeout=remaining_time
                    )
                    yield event
                except asyncio.TimeoutError:
                    LOGGER.debug("Event generator timeout: waiting for event on queue")
                    stop_event.set()
                except asyncio.CancelledError:
                    LOGGER.debug("Task cancelled")
                    stop_event.set()

        return EventGeneratorWrapper(
            event_generator(), self, wallet, topic, populate_task
        )

    async def _populate_client_queue(
        self, *, wallet: str, topic: str, client_id, client_queue: asyncio.Queue
    ):
        LOGGER.debug(
            "SSE Manager: start _populate_client_queue for wallet %s and topic %s",
            wallet,
            topic,
        )
        while True:
            queue_is_read = False
            if topic == WEBHOOK_TOPIC_ALL:
                for topic_key in self.lifo_cache[wallet].keys():
                    async with self.cache_locks[wallet][topic_key]:
                        lifo_queue = self.lifo_cache[wallet][topic_key]
                        try:
                            while True:
                                timestamp, event = lifo_queue.get_nowait()
                                queue_is_read = True
                                if time.time() - timestamp <= MAX_EVENT_AGE_SECONDS:
                                    async with self.client_locks[client_id]:
                                        await client_queue.put(event)

                                    self._client_last_accessed[
                                        client_id
                                    ] = datetime.now()
                        except asyncio.QueueEmpty:
                            # No event on lifo_queue, so we can continue
                            pass

                        if queue_is_read:
                            # We've consumed from the lifo_queue, so repopulate it before exiting lock:
                            lifo_queue, fifo_queue = await _copy_queue(
                                self.fifo_cache[wallet][topic], self.max
                            )
                            self.fifo_cache[wallet][topic] = fifo_queue
                            self.lifo_cache[wallet][topic] = lifo_queue
            else:
                async with self.cache_locks[wallet][topic]:
                    lifo_queue = self.lifo_cache[wallet][topic]
                    try:
                        while True:
                            timestamp, event = lifo_queue.get_nowait()
                            queue_is_read = True
                            if time.time() - timestamp <= MAX_EVENT_AGE_SECONDS:
                                async with self.client_locks[client_id]:
                                    await client_queue.put(event)
                                self._client_last_accessed[client_id] = datetime.now()
                    except asyncio.QueueEmpty:
                        # No event on lifo_queue, so we can continue
                        pass

                    if queue_is_read:
                        # We've consumed from the lifo_queue, so repopulate it before exiting lock:
                        lifo_queue, fifo_queue = await _copy_queue(
                            self.fifo_cache[wallet][topic], self.max
                        )
                        self.fifo_cache[wallet][topic] = fifo_queue
                        self.lifo_cache[wallet][topic] = lifo_queue

            await asyncio.sleep(CLIENT_QUEUE_POLL_PERIOD)

    async def _cleanup_queues(self):
        while True:
            # Wait for a while between cleanup operations
            await asyncio.sleep(QUEUE_CLEANUP_PERIOD)
            LOGGER.debug("SSE Manager: Running periodic cleanup task")

            # Iterate over all client queues
            for client_key in list(self.client_queues.keys()):
                # If a client queue hasn't been accessed in a while, remove it
                if datetime.now() - self.last_accessed[client_key] > timedelta(
                    seconds=MAX_EVENT_AGE_SECONDS
                ):
                    async with self.client_locks[client_key]:
                        del self.client_queues[client_key]
                        del self._client_last_accessed[client_key]
                    del self.client_locks[client_key]

            # Iterate over all cache queues
            for wallet in list(self.lifo_cache.keys()):
                for topic in list(self.lifo_cache[wallet].keys()):
                    if datetime.now() - self._cache_last_accessed[wallet][
                        topic
                    ] > timedelta(seconds=MAX_EVENT_AGE_SECONDS):
                        async with self.cache_locks[wallet][topic]:
                            del self.lifo_cache[wallet][topic]
                            del self.fifo_cache[wallet][topic]
                            del self._cache_last_accessed[wallet][topic]
                        del self.cache_locks[wallet][topic]

    async def cleanup_task(self, wallet: str, topic: str, populate_task: asyncio.Task):
        LOGGER.debug("SSE Manager: cleanup operation called for a populate_task")
        populate_task.cancel()
        async with self.cache_locks[wallet][topic]:
            # LIFO cache has been consumed; repopulate with events from FIFO cache:
            lifo_queue, fifo_queue = await _copy_queue(
                self.fifo_cache[wallet][topic], self.max
            )
            self.fifo_cache[wallet][topic] = fifo_queue
            self.lifo_cache[wallet][topic] = lifo_queue


async def _copy_queue(
    queue: asyncio.Queue, maxsize: int
) -> Tuple[asyncio.LifoQueue, asyncio.Queue]:
    # Consuming a queue removes its content. Therefore, we create two new queues to copy one
    LOGGER.debug("SSE Manager: Repopulating cache")
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


class EventGeneratorWrapper:
    def __init__(
        self,
        generator: AsyncGenerator[TopicItem, Any],
        sse_manager: SseManager,
        wallet: str,
        topic: str,
        populate_task: asyncio.Task,
    ):
        self.generator = generator
        self.sse_manager = sse_manager
        self.wallet = wallet
        self.topic = topic
        self.populate_task = populate_task

    async def __aenter__(self):
        return self.generator

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.generator.aclose()  # Close the async generator
        await self.sse_manager.cleanup_task(
            self.wallet, self.topic, self.populate_task
        )  # Call the cleanup method on the SseManager instance
