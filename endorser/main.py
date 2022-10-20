import logging
import os

import asyncio

from endorser.endorser_processor import listen_endorsement_events

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL)

# Set logger
logger = logging.getLogger(__name__)

logger.info("Starting endorser service")

loop = asyncio.get_event_loop()
loop.run_until_complete(listen_endorsement_events())
