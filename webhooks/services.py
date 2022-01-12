"""Services module."""

import json
from json.decoder import JSONDecodeError
from typing import List, Union
import re

from aioredis import Redis

from models import (
    ConnectionsHook,
    CredententialHookV2,
    CredentialHookV1,
    ProofsHookV1,
    ProofsHookV2,
    BasicMessagesHook,
    TopicItem,
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

    def _proof_hook_versioned(self, item: dict) -> dict:
        if "pres_ex_id" in item:
            item["pres_ex_id"] = "v2-" + item["pres_ex_id"]
            item = ProofsHookV2(**item)
        elif "presentation_exchange_id" in item:
            item["presentation_exchange_id"] = "v1-" + item["presentation_exchange_id"]
            item = ProofsHookV1(**item)
        return item

    def _credential_hook_versioned(self, item: dict) -> dict:
        if "cred_ex_id" in item:
            item["cred_ex_id"] = "v2-" + item["cred_ex_id"]
            item = CredententialHookV2(**item)
        elif "credential_exchange_id" in item:
            item["credential_exchange_id"] = "v1-" + item["credential_exchange_id"]
            item = CredentialHookV1(**item)
        return item

    def _version_connections(self, item: dict) -> dict:
        if item["connection_protocol"] == "didexchange/1.0":
            item["connection_id"] = "0023-" + item["connection_id"]
        elif item["connection_protocol"] == "connections/1.0":
            item["connection_id"] = "0016-" + item["connection_id"]
            print(item["connection_id"])
        item = ConnectionsHook(**item)
        return item

    def _deserialise(self, data: bytes) -> Union[str, dict]:
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
            return {"invalid JSON data": data}

    def _to_json(self, data: List[bytes]) -> List[dict]:
        data = [self._deserialise(val) for val in data]
        try:
            data = [json.loads(d) for d in data]
        except JSONDecodeError:
            # A multiline string has occured that has been split in
            # an invalid way wrt JSON format

            # Remove multiple spaces which occur when error msg is split into multiple lines
            # turn off black formatter here because it replaces the regex
            # fmt: off
            data = [re.sub('\s+',' ', d) for d in data]
            # Remove \" \" from the multiline error message because that is invalid json
            data = [d.replace('\" \"', ' ') for d in data]
            # fmt: on
            data = [json.loads(d) for d in data]
        return data

    def _to_model(self, topic: str, data: List[dict]) -> List[TopicItem]:
        data = self._to_json(data=data)

        if self._is_proof(topic):
            data = [self._proof_hook_versioned(d) for d in data]
        elif self._is_credential(topic):
            data = [self._credential_hook_versioned(d) for d in data]
        elif topic == "connections":
            data = [self._version_connections(d) for d in data]
        elif topic == "basicmessages":
            data = [BasicMessagesHook(**d) for d in data]
        return (
            [TopicItem(topic=topic, payload=payload) for payload in data]
            if data
            else []
        )

    async def add_topic_entry(self, topic: str, hook: bytes):
        return await self._redis.sadd(topic, hook)

    async def get_all_by_topic(self, topic: str) -> List[TopicItem]:

        data = await self._redis.smembers(topic)

        items = self._to_model(topic=topic, data=data)
        return items
