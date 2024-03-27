import asyncio
import json
from typing import Any, Dict, List, NoReturn

from fastapi import HTTPException

from shared.constants import LAGO_API_KEY, LAGO_URL
from shared.log_config import get_logger
from shared.util.rich_async_client import RichAsyncClient
from webhooks.models.billing_payloads import (
    AttribBillingEvent,
    BillingEvent,
    CredDefBillingEvent,
    CredentialBillingEvent,
    EndorsementBillingEvent,
    ProofBillingEvent,
    RevocationBillingEvent,
    RevRegDefBillingEvent,
    RevRegEntryBillingEvent,
)
from webhooks.services.webhooks_redis_serivce import WebhooksRedisService

logger = get_logger(__name__)


class BillingManager:
    """
    Class process billing events and send them to LAGO
    """

    def __init__(self, redis_service: WebhooksRedisService) -> None:
        self.redis_service = redis_service

        self._tasks: List[asyncio.Task] = []

        self._pubsub = None

        self._client = RichAsyncClient(name="BillingManager")
        self._client.headers = {"Authorization": f"Bearer {LAGO_API_KEY}"}

        self._LAGO_URL = LAGO_URL

    def start(self) -> None:
        """
        Start the billing manager
        """
        asyncio.create_task(
            self._listen_for_billing_events(), name="Listen for new billing events"
        )

    async def stop(self) -> None:
        """
        Wait for tasks to complete and stop the billing manager
        """
        for task in self._tasks:
            task.cancel()  # Request cancellation of the task
            try:
                await task  # Wait for the task to be cancelled
            except asyncio.CancelledError:
                pass
        self._tasks.clear()  # Clear the list of tasks
        logger.info("Billing manager stopped")

        if self._pubsub:
            self._pubsub.disconnect()
            logger.info("Billing pubsub disconnected")
