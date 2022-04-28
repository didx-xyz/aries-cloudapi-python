"""Services module."""

import json
from typing import Any, List

from aioredis import Redis

from models import (
    to_credential_hook_model,
    to_proof_hook_model,
    to_connections_model,
)
from shared_models import (
    TopicItem,
    RedisItem,
    Connection,
    CredentialExchange,
    PresentationExchange,
    BasicMessage,
    PayloadType,
    Endorsement,
)


class Service:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def _is_proof(self, topic: str) -> bool:
        proofs_identifiers = ["present_proof", "present_proof_v2_0"]
        return topic in proofs_identifiers

    def _is_credential(self, topic: str) -> bool:
        credential_identifiers = ["issue_credential", "issue_credential_v2_0"]
        return topic in credential_identifiers

    def _proof_hook_versioned(self, item: RedisItem) -> PresentationExchange:
        return to_proof_hook_model(item=item)

    def _credential_hook_versioned(self, item: RedisItem) -> CredentialExchange:
        return to_credential_hook_model(item=item)

    def _version_connections(self, item: RedisItem) -> Connection:
        return to_connections_model(item=item)

    def _basic_messages(self, item: RedisItem) -> BasicMessage:
        basic_message = BasicMessage(**item["payload"])

        return basic_message

    def _endorsements(self, item: RedisItem):
        endorsement = Endorsement(**item["payload"])
        endorsement.state = endorsement.state.replace("_", "-")

        return endorsement

    def _to_item(self, data: RedisItem):
        item = None

        # Transform the data to the appropriate model
        if data["topic"] == "proofs":
            item = self._proof_hook_versioned(data)
        elif data["topic"] == "credentials":
            item = self._credential_hook_versioned(data)
        elif data["topic"] == "connections":
            item = self._version_connections(data)
        elif data["topic"] == "basic-messages":
            item = self._basic_messages(data)
        elif data["topic"] == "endorsements":
            item = self._endorsements(data)

        return item

    def _to_topic_item(
        self, data: RedisItem, payload: PayloadType
    ) -> TopicItem[PayloadType]:
        return TopicItem[PayloadType](
            topic=data["topic"],
            wallet_id=data["wallet_id"],
            origin=data["origin"],
            payload=payload,
        )

    async def add_topic_entry(self, topic: str, hook: str):
        await self._redis.sadd(topic, hook)

    async def transform_topic_entry(self, data: RedisItem):
        """Transfroms an entry from the redis cache into model."""
        payload = self._to_item(data=data)

        # Only return payload if recognized event
        if payload:
            return self._to_topic_item(data=data, payload=payload)

    async def get_all_by_wallet(self, wallet_id: str):
        # Get the data from redis queue
        data_list: List[TopicItem[Any]] = []
        entries = await self._redis.smembers(wallet_id)

        for entry in entries:
            data: RedisItem = json.loads(entry)
            webhook = await self.transform_topic_entry(data)

            if webhook:
                data_list.append(webhook)

        return data_list

    async def get_all_for_topic_by_wallet_id(
        self, topic: str, wallet_id: str
    ) -> List[TopicItem[Any]]:
        data_list: List[TopicItem[Any]] = []
        entries = await self._redis.smembers(wallet_id)

        for entry in entries:
            data: RedisItem = json.loads(entry)
            # Only take current topic
            if data["topic"] != topic:
                continue

            webhook = await self.transform_topic_entry(data)

            if webhook:
                data_list.append(webhook)

        return data_list
