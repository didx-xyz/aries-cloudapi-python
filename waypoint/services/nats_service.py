import asyncio
import json
import math
import time
from typing import Any, AsyncGenerator, Generator, List

import nats
from nats.aio.client import Client as NATS
from nats.errors import TimeoutError
from nats.js.api import ConsumerConfig
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
    nats_client.close()
    logger.debug("NATS connection closed")


class NatsEventsProcessor:
    def __init__(self, jetstream: JetStreamContext):
        self.js_context: JetStreamContext = jetstream
        self._tasks: List[asyncio.Task] = []

    async def start(self):
        # TODO: Implement
        pass

    async def stop(self):
        # TODO: Implement
        pass

