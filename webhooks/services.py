"""Services module."""

import json
from typing import List

from aioredis import Redis

from models import (
    BasicMessagesHook,
    to_credentential_hook_model,
    to_proof_hook_model,
    to_connections_model,
)
from shared_models import TopicItem

topics = [
    "connections",
    "issue_credential",
    "forward",
    "ping",
    "basicmessages",
    "issuer_cred_rev",
    "issue_credential_v2_0",
    "issue_credential_v2_0_indy",
    "issue_credential_v2_0_dif",
    "present_proof",
    "present_proof_v2_0",
    "revocation_registry",
]


class Service:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def _is_proof(self, topic: str) -> bool:
        proofs_identifiers = ["present_proof", "present_proof_v2_0"]
        return topic in proofs_identifiers

    def _is_credential(self, topic: str) -> bool:
        credential_identifiers = ["issue_credential", "issue_credential_v2_0"]
        return topic in credential_identifiers

    def _proof_hook_versioned(self, item: dict) -> dict:
        return to_proof_hook_model(item=item)

    def _credential_hook_versioned(self, item: dict) -> dict:
        return to_credentential_hook_model(item=item)

    def _version_connections(self, item: dict) -> dict:
        return to_connections_model(item=item)

    def _to_item(self, topic: str, data: List[dict]) -> List[dict]:
        # Transform the data to the appropriate model
        if self._is_proof(topic):
            data = [self._proof_hook_versioned(d) for d in data]
        elif self._is_credential(topic):
            data = [self._credential_hook_versioned(d) for d in data]
        elif topic == "connections":
            data = [self._version_connections(d) for d in data]
        elif topic == "basicmessages":
            data = [BasicMessagesHook(**d) for d in data]
        return data

    def _to_topic_item(self, topic: str, data: List[dict]) -> List[TopicItem]:
        topic_data = (
            [
                TopicItem(
                    topic=topic,
                    wallet_id=payload.wallet_id,
                    origin=payload.origin,
                    payload=payload,
                )
                for payload in data
            ]
            if data
            else []
        )
        return topic_data

    async def add_topic_entry(self, topic: str, hook: str) -> List[TopicItem]:
        return await self._redis.sadd(topic, hook)

    async def get_all_by_wallet(self, wallet_id: str) -> List[TopicItem]:
        # Get the data from redis queue
        data_list = []
        data = await self._redis.smembers(wallet_id)
        data = [json.loads(d) for d in data]
        for topic in topics:
            topic_data = [d for d in data if d["topic"] == topic]
            topic_data = self._to_item(topic=topic, data=topic_data)
            topic_data = self._to_topic_item(topic=topic, data=topic_data)
            if topic_data:
                data_list.extend(topic_data)
        return data_list

    async def get_all_for_topic_by_wallet_id(
        self, topic: str, wallet_id: str
    ) -> List[TopicItem]:
        data = await self._redis.smembers(wallet_id)
        data = [json.loads(d) for d in data]
        data = [d for d in data if d["topic"] == topic]
        data = self._to_item(topic=topic, data=data)
        topic_data = self._to_topic_item(topic=topic, data=data)
        return topic_data
