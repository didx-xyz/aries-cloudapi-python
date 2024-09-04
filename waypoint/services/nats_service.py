import asyncio
import json
import time
from typing import Any, AsyncGenerator, List

import nats
from nats.aio.client import Client as NATS
from nats.errors import BadSubscriptionError, Error, TimeoutError
from nats.js.api import ConsumerConfig, DeliverPolicy
from nats.js.client import JetStreamContext

from shared.constants import (
    NATS_CREDS_FILE,
    NATS_SERVER,
    NATS_START_TIME,
    NATS_STREAM,
    NATS_SUBJECT,
)
from shared.log_config import get_logger
from shared.models.webhook_events import CloudApiWebhookEventGeneric
from waypoint.util.event_generator_wrapper import EventGeneratorWrapper

logger = get_logger(__name__)


async def init_nats_client() -> AsyncGenerator[JetStreamContext, Any]:
    """
    Initialize a connection to the NATS server.
    """
    logger.info("Connecting to NATS server...")
    try:
        nats_client: NATS = await nats.connect(
            servers=[NATS_SERVER], user_credentials=NATS_CREDS_FILE
        )
    except Exception as e:
        logger.error(f"Error connecting to NATS server: {e}")
        raise e
    logger.debug("Connected to NATS server")

    jetstream: JetStreamContext = nats_client.jetstream()
    logger.debug("Yielding JetStream context...")
    yield jetstream

    logger.info("Closing NATS connection...")
    await nats_client.close()
    logger.debug("NATS connection closed")


class NatsEventsProcessor:
    # TODO add a logger and check error handling
    def __init__(self, jetstream: JetStreamContext):
        self.js_context: JetStreamContext = jetstream
        self._tasks: List[asyncio.Task] = []

    async def stop(self):
        logger.debug("Stopping NATS event processor...")

        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.debug("Task was cancelled successfully")

        logger.info("NATS event processor stopped.")

    async def _subscribe(
        self, group_id: str, wallet_id: str
    ) -> JetStreamContext.PullSubscription:
        try:
            logger.debug("Subscribing to JetStream...")
            config = ConsumerConfig(
                deliver_policy="by_start_time",
                opt_start_time=start_time,
                inactive_threshold=130,
            )

            logger.error(
                f"Subscribing to {NATS_SUBJECT}.{group_id}.{wallet_id} on nats stream {NATS_STREAM} with start time {start_time} and config\n {config}"
            )
            subscription = await self.js_context.pull_subscribe(
                subject=f"{NATS_SUBJECT}.{group_id}.{wallet_id}",
                stream=NATS_STREAM,
                config=config,
            )
        except Exception as e:
            logger.error(f"Error subscribing to NATS: {e}")
            raise e

        return subscription

    async def process_events(
        self,
        group_id: str,
        wallet_id: str,
        topic: str,
        stop_event: asyncio.Event,
        duration: int = 150,
    ):
        logger.info(
            f"Processing events for group {group_id} and wallet {wallet_id} on topic {topic}"
        )

        subscription = await self._subscribe(group_id=group_id, wallet_id=wallet_id)

        async def event_generator() -> AsyncGenerator[CloudApiWebhookEventGeneric, Any]:
            end_time = time.time() + duration
            logger.trace(f"end_time: {end_time}")
            while not stop_event.is_set():
                remaining_time = remaining_time = end_time - time.time()
                logger.trace(f"remaining_time: {remaining_time}")
                if remaining_time <= 0:
                    logger.debug("Timeout reached")
                    stop_event.set()
                    break

                try:
                    messages = await subscription.fetch(10, 1)
                    for message in messages:
                        if message.headers.get("event_topic") == topic:
                            event = json.loads(message.data)
                            yield CloudApiWebhookEventGeneric(**event)
                        await message.ack()
                except TimeoutError:
                    logger.trace("Timeout fetching messages continuing...")
                    await asyncio.sleep(1)
                except asyncio.CancelledError:
                    logger.debug("Event generator cancelled")
                    stop_event.set()
                    break

        generator_wrapper = EventGeneratorWrapper(generator=event_generator())
        logger.trace("adding generator to tasks")
        task = asyncio.create_task(generator_wrapper)
        self._tasks.append(task)

        return generator_wrapper
