from typing import Any, AsyncGenerator

from shared.models.webhook_events import CloudApiWebhookEventGeneric


class EventGeneratorWrapper:
    """
    A wrapper class for managing an asynchronous generator alongside an asyncio task.

    This class encapsulates an async generator and a related asyncio task, providing
    a convenient way to manage their lifecycle together. It is used in the NatsEventsProcessor
    and Waypoint route.

    Attributes:
        generator: An asynchronous generator yielding CloudApiWebhookEventGeneric objects.

    Modified from code written by @ff137
    """
    def __init__(self, generator: AsyncGenerator[CloudApiWebhookEventGeneric, Any]):
        self.generator = generator

    async def __aenter__(self):
        """
        Enters the asynchronous context, returning the generator.
        """
        return self.generator

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Exits the asynchronous context, closing the generator

        Args:
            exc_type: The exception type, if any, that caused the context to be exited.
            exc_val: The exception value, if any.
            exc_tb: The traceback, if an exception occurred.
        """
        await self.generator.aclose()
