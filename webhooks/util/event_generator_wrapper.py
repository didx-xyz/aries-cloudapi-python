import asyncio
from typing import Any, AsyncGenerator

from shared.models.webhook_topics import CloudApiWebhookEventGeneric


class EventGeneratorWrapper:
    """
    A wrapper class for managing an asynchronous generator alongside an asyncio task.

    This class encapsulates an async generator and a related asyncio task, providing
    a convenient way to manage their lifecycle together. It is used in the SseManager
    and SSE routes.

    Attributes:
        generator: An asynchronous generator yielding CloudApiWebhookEventGeneric objects.
        populate_task: An asyncio.Task object that populates the generator.
    """

    def __init__(
        self,
        generator: AsyncGenerator[CloudApiWebhookEventGeneric, Any],
        populate_task: asyncio.Task,
    ):
        """
        Initializes the EventGeneratorWrapper with an async generator and a populate task.

        Args:
            generator: An asynchronous generator yielding CloudApiWebhookEventGeneric objects.
            populate_task: An asyncio.Task object responsible for populating the generator.
        """
        self.generator = generator
        self.populate_task = populate_task

    async def __aenter__(self):
        """
        Enters the asynchronous context, returning the generator.
        """
        return self.generator

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Exits the asynchronous context, closing the generator and canceling the populate task.

        Args:
            exc_type: The exception type, if any, that caused the context to be exited.
            exc_val: The exception value, if any.
            exc_tb: The traceback, if an exception occurred.
        """
        await self.generator.aclose()  # Close the async generator
        self.populate_task.cancel()  # Ensure populate task is cancelled
