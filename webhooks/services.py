"""Services module."""

from aioredis import Redis


class Service:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def process(self, topic: str, hook: str) -> str:
        await self._redis.set(topic, hook)
        return await self._redis.get(topic)  # , encoding='utf-8')
