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
