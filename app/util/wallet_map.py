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


class ClientWalletMap:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def add_wallet_map(self, wallet_id: str, group: str) -> None:
        try:
            await self.redis.set(wallet_id, group)
        except Exception as e:
            raise e

    async def get_wallet_map(self, wallet_id: str) -> str:
        try:
            return await self.redis.get(wallet_id)
        except Exception as e:
            raise e
