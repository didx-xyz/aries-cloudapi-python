"""Services module."""

import json
from json.decoder import JSONDecodeError
from typing import List, Any

from aioredis import Redis
from pydantic import BaseModel


class TopicItem(BaseModel):
    topic: str
    payload: Any


class Service:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def __is_proof(self, topic: str) -> bool:
        proofs_identifiers = ["present_proof", "present_proof_v2_0"]
        return topic in proofs_identifiers

    def __is_credential(self, topic: str) -> bool:
        credential_identifiers = ["issue_credential", "issue_credential_v2_0"]
        return topic in credential_identifiers

    def __deserialise(self, data: bytes):
        try:
            return (
                data.decode("utf-8")
                .replace("\\\\", "\\")
                .replace("\n", "")
                .replace("'", '"')
                .replace("False", json.dumps(False))
                .replace("True", json.dumps(True))
            )
        except JSONDecodeError:
            return data

    # def _proof_hook_versioned(self, hook: bytes, topic: str) -> dict:
    #     hook_dict = self._hook_dict(hook=hook)
    #     hook_dict["credential_id"] = topic + hook_dict["credential_id"]
    #     return hook_dict

    #     hook_dict = json.loads(hook.decode("utf-8").replace("'", '"'))
    #     hook_dict["proof_"]
    #     return json.loads(hook.decode("utf-8").replace("'", '"'))

    async def add_topic_entry(self, topic: str, hook: bytes):
        return await self._redis.sadd(topic, hook)

    async def get_all_by_topic(self, topic: str) -> List[TopicItem]:
        data = await self._redis.smembers(topic)
        data = [self.__deserialise(val) for val in data]
        return [TopicItem(topic=topic, payload=json.loads(payload)) for payload in data]
