import asyncio
import logging
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any, Generator

from webhooks.dependencies.service import Service

LOGGER = logging.getLogger(__name__)


class SSEManager:
    """
    Class to manage Server-Sent Events (SSE).
    """

    def __init__(self, service: Service):
        self.service = service
        self.clients = defaultdict(lambda: defaultdict(list))
        self.lock = asyncio.Lock()  # Concurrency management

    @asynccontextmanager
    async def sse_event_stream(
        self, wallet_id: str, topic: str
    ) -> Generator[asyncio.Queue, Any, None]:
        """
        Create a SSE event stream for a topic using a provided service.

        Args:
            wallet_id: The ID of the wallet subscribing to the topic.
            topic: The topic for which to create the event stream.
            service: The service to use for fetching undelivered messages.
        """
        queue = asyncio.Queue()
        # Re-deliver undelivered messages
        try:
            webhooks_to_deliver = await self.service.get_all_for_topic_by_wallet_id(topic, wallet_id)
        except Exception as e:
            LOGGER.error(
                "Could not get undelivered messages for topic '%s': %r", topic, e
            )
            webhooks_to_deliver = []
            raise e

        for message in webhooks_to_deliver:
            await queue.put(message)

        async with self.lock:
            self.clients[wallet_id][topic].append(queue)

        try:
            yield queue
        finally:
            async with self.lock:
                self.clients[wallet_id][topic].remove(queue)

    @asynccontextmanager
    async def enqueue_sse_event(self, event: str, wallet_id: str, topic: str) -> None:
        """
        Enqueue a SSE event to be sent to a specific wallet for a specific topic.

        This function puts the event into the queue of the respective client.
        These events are then fetched from the queue and sent to the client
        via FastAPI's StreamingResponse.

        If there are no active clients for the given wallet and topic,
        it stores the event as an undelivered message using the provided service.

        Args:
            event: The event to enqueue.
            wallet_id: The ID of the wallet to which to enqueue the event.
            topic: The topic to which to enqueue the event.
            service: The service to use for storing undelivered messages.
        """
        LOGGER.debug(
            "Enqueueing event to wallet '%s' for topic '%s': %s",
            wallet_id,
            topic,
            event,
        )

        if self.clients[wallet_id][topic]:
            for queue in self.clients[wallet_id][topic]:
                await queue.put(event)
        else:
            try:
                await self.service.store_undelivered_message(wallet_id, topic, event)
            except Exception as e:
                LOGGER.error(
                    "Could not store undelivered message for wallet '%s', topic '%s': %r",
                    wallet_id,
                    topic,
                    e,
                )
