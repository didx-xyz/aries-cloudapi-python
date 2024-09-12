import asyncio
import json
import time
from typing import Any, AsyncGenerator, List

import nats
from nats.aio.client import Client as NATS
from nats.aio.errors import ErrConnectionClosed, ErrNoServers, ErrTimeout
from nats.errors import BadSubscriptionError, Error, TimeoutError
from nats.js.client import JetStreamContext

from shared.constants import NATS_CREDS_FILE, NATS_SERVER, NATS_STREAM, NATS_SUBJECT
from shared.log_config import get_logger
from shared.models.webhook_events import CloudApiWebhookEventGeneric
from waypoint.util.event_generator_wrapper import EventGeneratorWrapper

logger = get_logger(__name__)


async def init_nats_client() -> AsyncGenerator[JetStreamContext, Any]:
    """
    Initialize a connection to the NATS server.
    """
    logger.debug("Connecting to NATS server...")
    try:
        connect_kwargs = {
            "servers": [NATS_SERVER],
        }
        if NATS_CREDS_FILE:
            connect_kwargs["user_credentials"] = NATS_CREDS_FILE

            nats_client: NATS = await nats.connect(**connect_kwargs)
        else:
            logger.warning("No NATS credentials file found, assuming local development")
            nats_client: NATS = await nats.connect(**connect_kwargs)

    except (ErrConnectionClosed, ErrTimeout, ErrNoServers) as e:
        logger.error(f"Error connecting to NATS server: {e}")
        raise e
    logger.debug("Connected to NATS server")

    jetstream: JetStreamContext = nats_client.jetstream()
    logger.debug("Yielding JetStream context...")
    yield jetstream

    logger.debug("Closing NATS connection...")
    await nats_client.close()
    logger.debug("NATS connection closed")


class NatsEventsProcessor:
    """
    Class to handle processing of NATS events. Calling the process_events method will
    subscribe to the NATS server and return an async generator that will yield events
    """

    def __init__(self, jetstream: JetStreamContext):
        self.js_context: JetStreamContext = jetstream
        self._tasks: List[asyncio.Task] = []

    async def stop(self):
        logger.debug("Stopping NATS event processor...")
        # TODO - Need to decide how to handle stopping the event processor

        logger.debug("NATS event processor stopped.")

    async def _subscribe(
        self, group_id: str, wallet_id: str
    ) -> JetStreamContext.PullSubscription:
        try:
            logger.debug("Subscribing to JetStream...")
            if group_id:

                logger.trace("Tenant-admin call got group_id: {}", group_id)
                subscribe_kwargs = {
                    "subject": f"{NATS_SUBJECT}.{group_id}.{wallet_id}",
                    "stream": NATS_STREAM,
                }
            else:
                logger.trace("Tenant call got no group_id")
                subscribe_kwargs = {
                    "subject": f"{NATS_SUBJECT}.*.{wallet_id}",
                    "stream": NATS_STREAM,
                }
            subscription = await self.js_context.pull_subscribe(**subscribe_kwargs)

            return subscription

        except BadSubscriptionError as e:
            logger.error(f"BadSubscriptionError subscribing to NATS: {e}")
            raise
        except Error as e:
            logger.error(f"Error subscribing to NATS: {e}")
            raise
        except Exception as e:
            logger.error(f"Unknown error subscribing to NATS: {e}")
            raise

    async def process_events(
        self,
        group_id: str,
        wallet_id: str,
        topic: str,
        stop_event: asyncio.Event,
        duration: int = 10,
    ):
        logger.debug(
            f"Processing events for group {group_id} and wallet {wallet_id} on topic {topic}"
        )

        subscription = await self._subscribe(group_id=group_id, wallet_id=wallet_id)

        async def event_generator() -> AsyncGenerator[CloudApiWebhookEventGeneric, Any]:
            end_time = time.time() + duration
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

        return EventGeneratorWrapper(generator=event_generator())
