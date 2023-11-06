from typing import AsyncIterator, List, Optional

import aioredis
from aioredis import Redis
from pydantic import BaseModel, ValidationError

from shared.log_config import get_logger
from shared.models.webhook_topics import (
    AcaPyWebhookEvent,
    CloudApiWebhookEvent,
    PayloadType,
)
from shared.util.rich_parsing import parse_with_error_handling
from webhooks.models import map_topic_to_transformer

logger = get_logger(__name__)


async def init_redis_pool(host: str, password: str) -> AsyncIterator[Redis]:
    pool = await aioredis.from_url(f"redis://{host}", password=password)
    yield pool
    pool.close()
    await pool.wait_closed()


class RedisService:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def _to_item(self, data: AcaPyWebhookEvent) -> Optional[BaseModel]:
        transformer = map_topic_to_transformer.get(data.topic)

        if transformer:
            return transformer(data)

        logger.warning("No transformer for topic: `{}`", data.topic)
        return None

    def _to_topic_item(
        self, data: AcaPyWebhookEvent, payload: PayloadType
    ) -> CloudApiWebhookEvent:
        return CloudApiWebhookEvent(
            topic=data.topic,
            wallet_id=data.wallet_id,
            origin=data.origin,
            payload=payload,
        )

    def transform_topic_entry(
        self, data: AcaPyWebhookEvent
    ) -> List[CloudApiWebhookEvent]:
        """Transforms an entry from the redis cache into model."""
        payload = self._to_item(data=data)

        # Only return payload if recognized event
        if payload:
            return self._to_topic_item(data=data, payload=payload)

        return None  # If transformer doesn't exist, warning already logged

    def _transform_redis_entries(
        self, entries: List[str], topic: Optional[str] = None
    ) -> List[CloudApiWebhookEvent]:
        logger.debug("Transform redis entries to model types")
        data_list: List[CloudApiWebhookEvent] = []
        for entry in entries:
            try:
                data: AcaPyWebhookEvent = parse_with_error_handling(
                    AcaPyWebhookEvent, entry
                )
                # Only take current topic
                if topic and data.topic != topic:
                    continue

                webhook = self.transform_topic_entry(data)

                if webhook:
                    data_list.append(webhook)
            # Log the data failing to create webhook, skip appending
            # anything to the list, and continue to next item in entries
            except ValidationError:
                logger.exception(
                    "Error creating formatted webhook for data entry: `{}`.", entry
                )
            # Catch the general case if sth else/unknown occurs:
            except Exception:
                logger.exception("Unknown exception occurred.")

        logger.debug("Returning transformed redis entries.")
        return data_list

    async def get_all_by_wallet(self, wallet_id: str) -> List[CloudApiWebhookEvent]:
        bound_logger = logger.bind(body={"wallet_id": wallet_id})
        bound_logger.debug("Fetching entries from redis by wallet id")
        entries = await self._redis.smembers(wallet_id)
        bound_logger.debug("Successfully fetched redis entries.")
        return self._transform_redis_entries(entries)

    async def get_all_for_topic_by_wallet_id(
        self, topic: str, wallet_id: str
    ) -> List[CloudApiWebhookEvent]:
        bound_logger = logger.bind(body={"wallet_id": wallet_id, "topic": topic})
        bound_logger.debug("Fetching entries from redis by wallet id")
        entries = await self._redis.smembers(wallet_id)
        bound_logger.debug("Successfully fetched redis entries.")
        return self._transform_redis_entries(entries, topic)

    async def add_wallet_entry(self, redis_item: AcaPyWebhookEvent) -> None:
        wallet_id = redis_item.wallet_id
        event_json = redis_item.model_dump_json()
        bound_logger = logger.bind(body={"wallet_id": wallet_id, "event": event_json})
        bound_logger.debug("Write entry to redis")
        await self._redis.sadd(wallet_id, event_json)
        bound_logger.debug("Successfully wrote entry to redis.")
