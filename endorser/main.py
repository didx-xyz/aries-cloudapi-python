import asyncio

from endorser.endorser_processor import listen_endorsement_events
from shared.log_config import get_logger

logger = get_logger("endorser.main")  # override as __name__ gets passed as __main__

if __name__ == "__main__":
    logger.info("Starting endorser service")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(listen_endorsement_events())
