import asyncio
from typing import Any, Dict, Optional

from app.webhooks import Webhooks
from shared_models import CloudApiTopics


class Listener:
    def __init__(self, topic: CloudApiTopics, wallet_id: str):
        self.topic = topic
        self.wallet_id = wallet_id
        self.queue = asyncio.Queue()

    async def on_webhook(self, data: Dict[str, Any]):
        if data["topic"] == self.topic and data["wallet_id"] == self.wallet_id:
            await self.queue.put(data)

    def _payload_matches_filter(self, payload: Dict[str, Any], filter_map: Dict[str, Any]) -> bool:
        return all(
            key in payload and payload.get(key, None) == filter_value
            for key, filter_value in filter_map.items()
        )

    async def wait_for_event(self, filter_map: Dict[str, Any]) -> Dict[str, Any]:
        while not self.queue.empty():
            item = await self.queue.get()

            payload = item["payload"]

            if self._payload_matches_filter(payload, filter_map):
                return payload

        # Return None or raise an exception if no matching payload is found
        return None

    async def wait_for_event_with_timeout(self, filter_map: Dict[str, Any], timeout: float = 180):
        try:
            payload = await asyncio.wait_for(self.wait_for_event(filter_map), timeout=timeout)
            return payload
        except Exception:
            raise
        finally:
            await self.stop()

    async def start(self):
        await Webhooks.register_listener(self.on_webhook)

    async def stop(self):
        Webhooks.unregister_listener(self.on_webhook)
