import asyncio

from endorser.config.log_config import get_logger
from endorser.endorser_processor import listen_endorsement_events

logger = get_logger(__name__)

if __name__ == "__main__":
    logger.info("Starting endorser service")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(listen_endorsement_events())
