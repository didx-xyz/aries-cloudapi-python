"""Services module."""

from typing import List, Optional

from aioredis import Redis
from aries_cloudcontroller.model import OobRecord
from pydantic import ValidationError

from shared import (
    BasicMessage,
    Connection,
    CredentialExchange,
    Endorsement,
    PayloadType,
    PresentationExchange,
    RedisItem,
    TopicItem,
)
from shared.util.rich_parsing import parse_with_error_handling
from webhooks.config.log_config import get_logger
from webhooks.models import (
    to_connections_model,
    to_credential_hook_model,
    to_endorsement_model,
    to_proof_hook_model,
)

logger = get_logger(__name__)


class Service:
    def __init__(self, redis: Redis):
        self._redis = redis

    def _proof_hook_versioned(self, item: RedisItem) -> PresentationExchange:
        return to_proof_hook_model(item=item)

    def _credential_hook_versioned(self, item: RedisItem) -> CredentialExchange:
        return to_credential_hook_model(item=item)

    def _version_connections(self, item: RedisItem) -> Connection:
        return to_connections_model(item=item)

    def _endorsements(self, item: RedisItem) -> Endorsement:
        return to_endorsement_model(item=item)

    def _basic_messages(self, item: RedisItem) -> BasicMessage:
        return BasicMessage(**item.payload)

    def _oob(self, item: RedisItem) -> OobRecord:
        return OobRecord(**item.payload)

    def _to_item(self, data: RedisItem):
        item = None
        topic = data.topic
        # Transform the data to the appropriate model
        if topic == "proofs":
            item = self._proof_hook_versioned(data)
        elif topic == "credentials":
            item = self._credential_hook_versioned(data)
        elif topic == "connections":
            item = self._version_connections(data)
        elif topic == "basic-messages":
            item = self._basic_messages(data)
        elif topic == "endorsements":
            item = self._endorsements(data)
        elif topic == "oob":
            item = self._oob(data)

        return item

    def _to_topic_item(self, data: RedisItem, payload: PayloadType) -> TopicItem:
        return TopicItem(
            topic=data.topic,
            wallet_id=data.wallet_id,
            origin=data.origin,
            payload=payload,
        )

    def transform_topic_entry(self, data: RedisItem) -> List[TopicItem]:
        """Transforms an entry from the redis cache into model."""
        payload = self._to_item(data=data)

        # Only return payload if recognized event
        if payload:
            return self._to_topic_item(data=data, payload=payload)

    def _transform_redis_entries(
        self, entries: List[str], topic: Optional[str] = None
    ) -> List[TopicItem]:
        data_list: List[TopicItem] = []
        for entry in entries:
            try:
                data: RedisItem = parse_with_error_handling(RedisItem, entry)
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
                    "Error creating formatted webhook for data entry: {}.", entry
                )
            # Catch the general case if sth else/unknown occurs:
            except Exception:
                logger.exception("Unknown exception occurred.")

        return data_list

    async def get_all_by_wallet(self, wallet_id: str) -> List[TopicItem]:
        entries = await self._redis.smembers(wallet_id)
        return self._transform_redis_entries(entries)

    async def get_all_for_topic_by_wallet_id(
        self, topic: str, wallet_id: str
    ) -> List[TopicItem]:
        entries = await self._redis.smembers(wallet_id)
        return self._transform_redis_entries(entries, topic)

    async def add_wallet_entry(self, wallet_id: str, event: str) -> None:
        await self._redis.sadd(wallet_id, event)

    async def store_undelivered_message(self, topic: str, event: str) -> None:
        await self._redis.rpush(f"undelivered:{topic}", event)

    async def get_undelivered_messages(self, topic: str) -> List[str]:
        messages = await self._redis.lrange(f"undelivered:{topic}", 0, -1)
        await self._redis.delete(f"undelivered:{topic}")
        return [message.decode("utf-8") for message in messages]
