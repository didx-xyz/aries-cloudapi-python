import os
import aioredis

from dependency_injector import containers, providers
from typing import AsyncIterator
from aioredis import Redis

MT_REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")


async def init_wallet_map_redis_pool(host: str, password: str) -> AsyncIterator[Redis]:
    pool = await aioredis.from_url(f"redis://{host}", password=password)

    yield pool

    await pool.close()
