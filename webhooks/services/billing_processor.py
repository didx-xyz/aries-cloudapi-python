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

    def are_task_running(self) -> bool:
        """
        Check if tasks are running
        """
        logger.debug("Checking if tasks are running")

        if not self._pubsub:
            logger.error("Pubsub is not running")

        all_running = self._tasks and all(not task.done() for task in self._tasks)
        logger.debug("All tasks running: {}", all_running)

        if not all_running:
            for task in self._tasks:
                if task.done():
                    logger.warning("Task `{}` is not running", task.get_name())
        return self._pubsub and all_running

    async def _listen_for_billing_events(
        self, max_retries=5, retry_duration=1
    ) -> NoReturn:
        """
        Listen for billing events, passs them to the billing processor
        """
        retry_count = 0
        sleep_duration = 1

        while retry_count < max_retries:
            try:
                logger.info("Creating pubsub instance")
                self._pubsub = self.redis_service.redis.pubsub()

                logger.info("Subscribing to billing event channel")
                self._pubsub.subscribe(self.redis_service.billing_event_pubsub_channel)

                # reset retry count. Unlikely to need to reconnect to pubsub
                retry_count = 0

                logger.info("Listening for billing events")
                while True:
                    message = self._pubsub.get_message(ignore_subscribe_messages=True)
                    if message:
                        logger.debug(f"Received billing message: >>{message}<<")
                        await self._process_billing_event(message)
                    else:
                        logger.trace("message is empty, retry in {}s", sleep_duration)
                        await asyncio.sleep(sleep_duration)
            except ConnectionError as e:
                logger.error("ConnectionError detected: {}.", e)
            except Exception:  # General exception catch
                logger.exception("Unexpected error.")

            retry_count += 1
            logger.warning(
                "Attempt #{} to reconnect in {}s ...", retry_count, retry_duration
            )
            await asyncio.sleep(retry_duration)  # Wait a bit before retrying
