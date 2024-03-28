import asyncio
from typing import Any, Dict, List, NoReturn

import orjson
from fastapi import HTTPException

from shared.constants import LAGO_API_KEY, LAGO_URL
from shared.log_config import get_logger
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

        self._client = RichAsyncClient(
            name="BillingManager", headers={"Authorization": f"Bearer {LAGO_API_KEY}"}
        )

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
        payload = event.get("payload")
        if topic == "credentials":
            # handel credentials event
            lago = self._convert_credential_event(group_id=group_id, payload=payload)

        elif topic == "proofs":
            # handel proofs event
            lago = self._convert_proofs_event(group_id=group_id, payload=payload)

        elif topic == "endorsements":
            # handel endorsements event
            lago = self._convert_endorsements_event(group_id=group_id, payload=payload)

        elif topic == "issuer_cred_rev":
            # handel issuer_cred_rev event
            lago = self._convert_issuer_cred_rev_event(
                group_id=group_id, payload=payload
            )

        else:
            logger.warning("Unknown billing event: {}", event)
            return

        # post billing event to LAGO
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

            logger.info("Response from LAGO: {}", lago_response.json())

        except HTTPException as e:
            if e.status_code == 422 and "value_already_exist" in e.detail:
                logger.debug("Error posting billing event >>> : {}", e.detail)

            else:
                logger.error("Error posting billing event: {}", e)
                raise e

    def _convert_credential_event(
        self, group_id: str, payload: Dict[str, Any]
    ) -> CredentialBillingEvent:
        """
        Convert credential event to LAGO event
        """
        logger.debug("Converting credential event: {}", payload)

        # using thread_id as transaction_id
        lago_event = CredentialBillingEvent(
            transaction_id=payload.get("thread_id"),
            external_customer_id=group_id,
        )
        return lago_event

    def _convert_proofs_event(
        self, group_id: str, payload: Dict[str, Any]
    ) -> ProofBillingEvent:
        """
        Convert proofs event to LAGO event
        """
        logger.debug("Converting proofs event: {}", payload)

        # using thread_id as transaction_id
        lago_event = ProofBillingEvent(
            transaction_id=payload.get("thread_id"),
            external_customer_id=group_id,
        )
        return lago_event

    def _convert_endorsements_event(
        self, group_id: str, payload: Dict[str, Any]
    ) -> LagoEvent:
        """
        Convert endorsements event to LAGO event
        """
        logger.debug("Converting endorsements event: {}", payload)

        # use operation type to determine the endorsement type
        # using transaction_id asfor LAGO transaction_id
        endorsement_type = payload.get("type")
        transaction_id = payload.get("transaction_id")
        if endorsement_type == "100":
            lago_event = AttribBillingEvent(
                transaction_id=transaction_id,
                external_customer_id=group_id,
            )
            return lago_event

        elif endorsement_type == "102":
            lago_event = CredDefBillingEvent(
                transaction_id=transaction_id,
                external_customer_id=group_id,
            )
            return lago_event

        elif endorsement_type == "113":
            lago_event = RevRegDefBillingEvent(
                transaction_id=transaction_id,
                external_customer_id=group_id,
            )
            return lago_event

        elif endorsement_type == "114":
            lago_event = RevRegEntryBillingEvent(
                transaction_id=transaction_id,
                external_customer_id=group_id,
            )
            return lago_event

        else:
            logger.warning("Unknown endorsement type: {}", endorsement_type)
            return

    def _convert_issuer_cred_rev_event(
        self, group_id: str, payload: Dict[str, Any]
    ) -> RevocationBillingEvent:
        """
        Convert issuer cred rev event to LAGO event
        """

        # using record_id as transaction_id
        logger.debug("Converting issuer cred rev event: {}", payload)
        lago_event = RevocationBillingEvent(
            transaction_id=payload.get("record_id"),
            external_customer_id=group_id,
        )
        return lago_event
