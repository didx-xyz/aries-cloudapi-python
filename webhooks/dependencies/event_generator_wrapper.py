import asyncio
from typing import Any, AsyncGenerator

from shared.models.topics import TopicItem


class EventGeneratorWrapper:
    def __init__(
        self,
        generator: AsyncGenerator[TopicItem, Any],
        populate_task: asyncio.Task,
    ):
        self.generator = generator
        self.populate_task = populate_task

    async def __aenter__(self):
        return self.generator

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.generator.aclose()  # Close the async generator
        self.populate_task.cancel()  # Ensure populate task is cancelled
