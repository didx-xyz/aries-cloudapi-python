import time
from typing import AsyncIterator, List

import aioredis
from aioredis import Redis

from shared.log_config import get_logger
from shared.models.webhook_topics.base import CloudApiWebhookEvent
from shared.util.rich_parsing import parse_with_error_handling

logger = get_logger(__name__)


async def init_redis_pool(host: str, password: str) -> AsyncIterator[Redis]:
    pool = await aioredis.from_url(f"redis://{host}", password=password)
    yield pool
    pool.close()
    await pool.wait_closed()


class RedisService:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

        self.sse_event_pubsub_channel = "new_sse_event"  # name of pub/sub channel

    async def add_webhook_event(self, wallet_id: str, event_json: str) -> None:
        bound_logger = logger.bind(body={"wallet_id": wallet_id, "event": event_json})
        bound_logger.debug("Write entry to redis")

        # get a nanosecond timestamp to identify this event
        timestamp_ns: int = time.time_ns()

        # Use the current timestamp as the score for the sorted set
        await self._redis.zadd(wallet_id, {event_json: timestamp_ns})

        broadcast_message = f"{wallet_id}:{timestamp_ns}"
        # publish that a new event has been added
        await self._redis.publish(self.sse_event_pubsub_channel, broadcast_message)

        bound_logger.debug("Successfully wrote entry to redis.")

    async def get_json_webhook_events_by_wallet(self, wallet_id: str) -> List[str]:
        bound_logger = logger.bind(body={"wallet_id": wallet_id})
        bound_logger.debug("Fetching entries from redis by wallet id")

        # Fetch all entries using the full range of scores
        entries: List[bytes] = await self._redis.zrange(wallet_id, 0, -1)
        entries_str: List[str] = [entry.decode() for entry in entries]

        bound_logger.debug("Successfully fetched redis entries.")
        return entries_str

    async def get_webhook_events_by_wallet(
        self, wallet_id: str
    ) -> List[CloudApiWebhookEvent]:
        entries = await self.get_json_webhook_events_by_wallet(wallet_id)
        parsed_entries = [
            parse_with_error_handling(CloudApiWebhookEvent, entry) for entry in entries
        ]
        return parsed_entries

    async def get_json_webhook_events_by_wallet_and_topic(
        self, wallet_id: str, topic: str
    ) -> List[str]:
        entries = await self.get_json_webhook_events_by_wallet(wallet_id)
        # Filter the json entry for our requested topic without deserialising
        topic_str = f'"topic":"{topic}"'
        return [entry for entry in entries if topic_str in entry]

    async def get_webhook_events_by_wallet_and_topic(
        self, wallet_id: str, topic: str
    ) -> List[CloudApiWebhookEvent]:
        entries = await self.get_webhook_events_by_wallet(wallet_id)
        return [entry for entry in entries if topic == entry.topic]

    async def get_json_events_by_timestamp(
        self, wallet_id: str, start_timestamp: float, end_timestamp: float = "+inf"
    ) -> List[str]:
        logger.debug("Fetching entries from redis by wallet id")
        entries = await self._redis.zrangebyscore(
            wallet_id, min=start_timestamp, max=end_timestamp
        )
        return entries

    async def get_events_by_timestamp(
        self, wallet_id: str, start_timestamp: float, end_timestamp: float = "+inf"
    ) -> List[CloudApiWebhookEvent]:
        entries = await self.get_json_events_by_timestamp(
            wallet_id, start_timestamp, end_timestamp
        )
        parsed_entries = [
            parse_with_error_handling(CloudApiWebhookEvent, entry) for entry in entries
        ]
        return parsed_entries
