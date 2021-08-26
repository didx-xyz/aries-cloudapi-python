"""Redis client module."""

from typing import AsyncIterator

import aioredis
from aioredis import Redis


async def init_redis_pool(host: str, password: str) -> AsyncIterator[Redis]:
    pool = await aioredis.from_url(f"redis://{host}", password=password)
    yield pool
    pool.close()
    await pool.wait_closed()
