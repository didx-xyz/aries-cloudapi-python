import os
from typing import AsyncIterator

import aioredis
from aioredis import Redis
from dependency_injector import containers, providers

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


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    redis_pool = providers.Resource(
        init_wallet_map_redis_pool,
        host=config.redis_host,
        password=config.redis_password,
    )

    redis_service = providers.Singleton(
        ClientWalletMap,
        redis=redis_pool,
    )


def get_container() -> Container:
    configured_container = Container()
    # Load configuration from environment variables with defaults
    configured_container.config.redis_host.from_env("REDIS_HOST", "localhost")
    configured_container.config.redis_password.from_env("REDIS_PASSWORD", "")
    return configured_container
