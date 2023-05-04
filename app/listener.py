import asyncio
from typing import Any, Dict

from shared_models import CloudApiTopics
from app.webhooks import Webhooks


class Listener:
    def __init__(self, topic: CloudApiTopics, wallet_id: str):
        self.topic = topic
        self.wallet_id = wallet_id
        self.queue = asyncio.Queue()

    async def on_webhook(self, data: Dict[str, Any]):
        if data["topic"] == self.topic and data["wallet_id"] == self.wallet_id:
            await self.queue.put(data)

    async def wait_for_event(self, filter_map: Dict[str, Any]) -> Dict[str, Any]:
        while True:
            item = await self.queue.get()

            payload = item["payload"]

            match = all(
                payload.get(filter_key, None) == filter_value
                for filter_key, filter_value in filter_map.items()
            )

            if match:
                return payload

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
