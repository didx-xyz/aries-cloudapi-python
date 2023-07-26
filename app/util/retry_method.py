import asyncio
from typing import Awaitable

from loguru import Logger


async def coroutine_with_retry(
    coroutine: Awaitable, logger: Logger, max_attempts=5, retry_delay=1
):
    for attempt in range(max_attempts):
        try:
            await coroutine
            break
        except Exception as e:
            if attempt + 1 == max_attempts:
                logger.error("Maximum number of retries exceeded. Failing.")
                raise e  # Re-raise the exception if max attempts exceeded

            logger.warning(
                f"Failed to run coroutine (attempt {attempt + 1}). Retrying in {retry_delay} seconds..."
            )
            await asyncio.sleep(retry_delay)
