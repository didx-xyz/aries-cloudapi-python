import asyncio
from typing import Any, Dict, List, NoReturn

import orjson
from fastapi import HTTPException

from shared.constants import LAGO_API_KEY, LAGO_URL
from shared.log_config import get_logger
from shared.models.endorsement import TransactionTypes
from shared.util.rich_async_client import RichAsyncClient
from webhooks.models.billing_payloads import (
    AttribBillingEvent,
    CredDefBillingEvent,
    CredentialBillingEvent,
    LagoEvent,
    ProofBillingEvent,
    RevocationBillingEvent,
    RevRegDefBillingEvent,
    RevRegEntryBillingEvent,
)
from webhooks.services.webhooks_redis_service import WebhooksRedisService

logger = get_logger(__name__)


class BillingManager:
    """
    Class process billing events and send them to LAGO
    """

    def __init__(self, redis_service: WebhooksRedisService) -> None:
        self.redis_service = redis_service

        self._tasks: List[asyncio.Task] = []

        self._pubsub = None

        self._client = RichAsyncClient(
            name="BillingManager", headers={"Authorization": f"Bearer {LAGO_API_KEY}"}
        )
        self.lago_api_key = LAGO_API_KEY

    def start(self) -> None:
        """
        Start the billing manager
        """
        if self.lago_api_key:
            self._tasks.append(
                asyncio.create_task(
                    self._listen_for_billing_events(),
                    name="Listen for new billing events",
                )
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

    def are_tasks_running(self) -> bool:
        """
        Check if tasks are running
        """
        logger.debug("Checking if tasks are running")
        # This is so that the health check can return True if the LAGO API key is not set
        # This is useful for local development and testing
        if not self.lago_api_key:
            return True

        if not self._pubsub:
            logger.warning("Pubsub is not running")

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
                        logger.debug("Received billing message: >>{}<<", message)
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

    async def _process_billing_event(self, message: Dict[str, Any]) -> None:
        """
        Process billing events. Convert them to LAGO events and post them to LAGO
        """
        message_data = message.get("data")
        if isinstance(message_data, bytes):
            message_data = message_data.decode("utf-8")

        group_id, timestamp_ns_str = message_data.split(":")
        timestamp_ns = int(timestamp_ns_str)

        events = self.redis_service.get_billing_event(
            group_id, timestamp_ns, timestamp_ns
        )

        if not events:
            # there are duplicate done event bc of acapy to cloudapi conversion
            # the score get updated and the event is not found with old score
            logger.debug(
                "No events found for group_id: {} and timestamp: {}",
                group_id,
                timestamp_ns,
            )
            return

        if len(events) > 1:
            logger.warning(
                "Multiple events found for group_id: {} and timestamp: {}",
                group_id,
                timestamp_ns,
            )

        event: Dict[str, Any] = orjson.loads(events[0])
        topic = event.get("topic")
        payload: Dict[str, Any] = event.get("payload")

        if topic == "credentials":
            thread_id = payload.get("thread_id")
            if not thread_id:
                logger.warning("No thread_id found for proof event: {}", event)
                return

            lago = CredentialBillingEvent(
                transaction_id=thread_id,
                external_customer_id=group_id,
            )

        elif topic == "proofs":
            thread_id = payload.get("thread_id")
            if not thread_id:
                logger.warning("No thread_id found for proof event: {}", event)
                return

            lago = ProofBillingEvent(
                transaction_id=thread_id,
                external_customer_id=group_id,
            )

        elif topic == "endorsements":

            endorsement_type = payload.get("type")
            transaction_id = payload.get("transaction_id")

            lago = self._convert_endorsements_event(
                group_id=group_id,
                endorsement_type=endorsement_type,
                transaction_id=transaction_id,
            )

            if not lago:
                logger.warning(
                    "No LAGO event created for endorsements event: {}", event
                )
                return

        elif topic == "issuer_cred_rev":
            record_id = payload.get("record_id")

            if not record_id:
                logger.warning("No record_id found for revocation event: {}", event)
                return

            lago = RevocationBillingEvent(
                transaction_id=record_id,
                external_customer_id=group_id,
            )

        else:
            logger.warning("Unknown topic for event: {}", event)
            return

        await self._post_billing_event(lago)

    async def _post_billing_event(self, event: LagoEvent) -> None:
        """
        Post billing event to LAGO
        """
        logger.debug("Posting billing event: {}", event)
        try:
            lago_response = await self._client.post(
                url=LAGO_URL,
                json={"event": event.model_dump()},
            )
            lago_response_json = lago_response.json()

            logger.info(
                "Response for event {} from LAGO: {}", event, lago_response_json
            )

        except HTTPException as e:
            if e.status_code == 422 and "value_already_exist" in e.detail:
                logger.warning(
                    "LAGO indicating transaction already received : {}", e.detail
                )
            else:
                logger.error("Error posting billing event to LAGO: {}", e.detail)

    def _convert_endorsements_event(
        self, group_id: str, transaction_id: str, endorsement_type: str
    ) -> LagoEvent | None:
        """
        Convert endorsements event to LAGO event
        """
        logger.debug(
            "Converting endorsements event with transaction_id: {} and endorsement_type: {}",
            transaction_id,
            endorsement_type,
        )

        lago_model = None
        lago = None
        if not transaction_id:
            logger.warning("No transaction_id found for endorsements event")
            return None

        lago_model = LagoEvent(
            transaction_id=transaction_id,
            external_customer_id=group_id,
        )

        # use operation type to determine the endorsement type
        # using transaction_id asfor LAGO transaction_id

        if endorsement_type == TransactionTypes.ATTRIB:
            lago = AttribBillingEvent(**lago_model.model_dump())

        elif endorsement_type == TransactionTypes.CLAIM_DEF:
            lago = CredDefBillingEvent(**lago_model.model_dump())

        elif endorsement_type == TransactionTypes.REVOC_REG_DEF:
            lago = RevRegDefBillingEvent(**lago_model.model_dump())

        elif endorsement_type == TransactionTypes.REVOC_REG_ENTRY:
            lago = RevRegEntryBillingEvent(**lago_model.model_dump())

        else:
            logger.warning("Unknown endorsement type: {}", endorsement_type)

        return lago
