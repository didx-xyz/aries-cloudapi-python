"""Services module."""

from aioredis import Redis


class Service:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def add_topic_entry(self, topic: str, hook: str):
        return await self._redis.sadd(topic, hook)

    async def get_all_by_topic(self, topic: str) -> str:
        return await self._redis.smembers(topic)
