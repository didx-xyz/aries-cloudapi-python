from typing import Any, AsyncGenerator

from shared.models.webhook_events import CloudApiWebhookEventGeneric


class EventGeneratorWrapper:
    def __init__(self, generator: AsyncGenerator[CloudApiWebhookEventGeneric, Any]):
        self.generator = generator

    async def __aenter__(self):
        # TODO add description
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
