import asyncio
import datetime
import sys
from typing import Any, Dict, List, NoReturn, Optional
from uuid import uuid4

import nats
import orjson
import xxhash
from nats.aio.client import Client as NATS
from nats.aio.errors import ErrConnectionClosed, ErrNoServers, ErrTimeout
from nats.js.client import JetStreamContext

from shared import APIRouter
from shared.constants import GOVERNANCE_LABEL, NATS_CREDS_FILE, NATS_SERVER, SET_LOCKS
from shared.log_config import get_logger
from shared.models.endorsement import (
    obfuscate_primary_data_in_payload,
    payload_is_applicable_for_endorser,
)
from shared.util.rich_parsing import parse_json_with_error_handling
from webhooks.models import AcaPyWebhookEvent, CloudApiWebhookEvent, topic_mapping
from webhooks.models.conversions import acapy_to_cloudapi_event
from webhooks.models.redis_payloads import AcaPyRedisEvent
from webhooks.services.billing_manager import is_applicable_for_billing
from webhooks.services.webhooks_redis_service import WebhooksRedisService

logger = get_logger(__name__)

router = APIRouter()


class AcaPyEventsProcessor:
    """
    Class to process ACA-Py webhook events that the plugin writes to redis.
    """

    def __init__(self, redis_service: WebhooksRedisService) -> None:
        self.redis_service = redis_service

        # Redis prefix for acapy events:
        self.acapy_redis_prefix = self.redis_service.acapy_redis_prefix

        # Event for indicating redis keyspace notifications
        self._new_event_notification = asyncio.Event()

        self._pubsub = None  # for managing redis pubsub connection
        self._pubsub_thread = None

        self._tasks: List[asyncio.Task] = []  # To keep track of running tasks

        self.nats_client: NATS = None
        self.jetstream: JetStreamContext = None

    def start(self) -> None:
        """
        Start the background tasks as part of AcaPyEventsProcessor's lifecycle
        """
        # self._start_notification_listener()  # disable as it is currently unused
        self._tasks.append(
            asyncio.create_task(
                self._process_incoming_events(), name="Process incoming events"
            )
        )
        logger.info("AcaPyEventsProcessor started.")

    async def stop(self) -> None:
        """
        Stops all background tasks gracefully.
        """
        for task in self._tasks:
            task.cancel()  # Request cancellation of the task
            try:
                await task  # Wait for the task to be cancelled
            except asyncio.CancelledError:
                pass  # Expected error upon cancellation, can be ignored
        self._tasks.clear()  # Clear the list of tasks

        if self._pubsub_thread:
            self._pubsub_thread.stop()
            logger.info("Stopped AcaPyEvents pubsub thread")

        if self._pubsub:
            await asyncio.sleep(0.1)  # allow thread to stop before disconnecting
            self._pubsub.disconnect()
            logger.info("Disconnected AcaPyEvents pubsub instance")

        logger.info("AcaPyEventsProcessor stopped.")

    def are_tasks_running(self) -> bool:
        """
        Checks if the background tasks are still running.

        Returns:
            True if all background tasks are running, False if any task has stopped.
        """
        logger.debug("Checking if all tasks are running")

        # todo: disabling pubsub thread check as it's currently unused and disconnects periodically on test env
        pubsub_thread_running = (
            True  # self._pubsub_thread and self._pubsub_thread.is_alive()
        )
        tasks_running = self._tasks and all(not task.done() for task in self._tasks)

        if not pubsub_thread_running:
            logger.error("Pubsub thread is not running")

        if not tasks_running:
            for task in self._tasks:
                if task.done():
                    logger.error("Task `{}` is not running", task.get_name())

        all_running = tasks_running and pubsub_thread_running

        logger.debug("All tasks running: {}", all_running)
        return all_running

    def _rpush_notification_handler(self, msg) -> None:
        """
        Processing handler for when rpush notifications are received
        """
        logger.trace("Received rpush notification: {}", msg)
        self._new_event_notification.set()

    def _start_notification_listener(self) -> None:
        """
        Listens for keyspace notifications from Redis and sets an event to resume processing.
        """
        # Example subscription pattern for keyspace notifications. Adjust as necessary.
        self._pubsub = self.redis_service.redis.pubsub()

        # Subscribe this pubsub channel to the notification pattern (rpush represents ACA-Py writing to list types)
        notification_pattern = "__keyevent@0__:rpush"
        self._pubsub.psubscribe(
            **{notification_pattern: self._rpush_notification_handler}
        )
        self._pubsub_thread = self._pubsub.run_in_thread(sleep_time=0.01)

        logger.info("Notification listener subscribed to redis keyspace notifications")

    async def _process_incoming_events(self) -> NoReturn:
        """
        Processing handler for incoming ACA-Py redis webhooks events
        """
        logger.info("Starting ACA-Py Events Processor")

        exception_count = 0
        max_exception_count = 5  # break inf loop after 5 consecutive exceptions

        attempts_without_events = 0
        max_attempts_without_events = sys.maxsize  # use max int to never stop
        sleep_duration = 0.1

        while True:
            try:
                batch_event_keys = self.redis_service.scan_keys(
                    match_pattern=self.acapy_redis_prefix, count=5000
                )
                if batch_event_keys:
                    attempts_without_events = 0  # Reset the counter
                    for list_key in batch_event_keys:  # the keys are of LIST type
                        logger.debug("Attempt to process list key: {}", list_key)
                        await self._attempt_process_list_events(list_key)

                else:
                    attempts_without_events += 1
                    if attempts_without_events >= max_attempts_without_events:
                        # Wait for a keyspace notification before continuing
                        logger.debug(
                            (
                                "Scan has returned no keys {} times in a row. "
                                "Waiting for keyspace notification..."
                            ),
                            max_attempts_without_events,
                        )
                        await self._new_event_notification.wait()
                        logger.debug("Keyspace notification triggered")
                        self._new_event_notification.clear()  # Reset the event for the next wait
                        attempts_without_events = 0  # Reset the counter
                    else:
                        await asyncio.sleep(sleep_duration)  # prevent a busy loop
                exception_count = 0  # reset exception count after successful loop
            except Exception:  # pylint: disable=W0718
                exception_count += 1
                logger.exception(
                    "Something went wrong while processing incoming events. Continuing..."
                )
                if exception_count >= max_exception_count:
                    raise  # exit inf loop

    async def _attempt_process_list_events(self, list_key: str) -> None:
        """
        Attempts to process a list-based event in Redis, ensuring that only one instance processes
        the event at a time by acquiring a lock.

        Args:
            list_key: The Redis key of the list to process.
        """
        lock_key = f"lock:{list_key}"

        if SET_LOCKS:
            lock_duration_ms = 3000  # milliseconds

            if self.redis_service.set_lock(lock_key, px=lock_duration_ms):
                logger.debug("Successfully set lock key for list index: {}", lock_key)
            else:
                logger.debug(
                    "Event {} is currently being processed by another instance.",
                    list_key,
                )
                return

            # Start a background task to extend the lock periodically
            # This is just to ensure that on the off chance that 3000ms isn't enough to process all the
            # events in the list, we want to avoid replicas processing the same webhook event twice
            extend_lock_task = self.redis_service.extend_lock_task(
                lock_key, interval=datetime.timedelta(milliseconds=lock_duration_ms)
            )
        else:
            extend_lock_task = None

        try:
            await self._process_list_events(list_key)
        except Exception as e:  # pylint: disable=W0718
            # if this particular event is unprocessable, we should remove it from the inputs, to avoid deadlocking
            logger.error("Processing {} raised an exception: {}", list_key, e)
            self._handle_unprocessable_event(list_key, e)
        finally:
            if SET_LOCKS:
                self._cleanup_lock(lock_key, extend_lock_task)

        return

    def _cleanup_lock(
        self, lock_key: str, extend_lock_task: Optional[asyncio.Task]
    ) -> None:
        if extend_lock_task:
            extend_lock_task.cancel()

        if not self.redis_service.delete_key(lock_key):
            logger.warning("Could not delete lock: {}. Perhaps it expired?", lock_key)
        else:
            logger.trace("Deleted lock key: {}", lock_key)

    async def _process_list_events(self, list_key) -> None:
        """
        Processes all events in a Redis list until the list is empty. Each event is processed individually,
        and upon successful processing, it's removed from the list.

        Args:
            list_key: The Redis key of the list to process.

        Returns:
            An exception if an error occurs during event processing; otherwise, returns None.
        """
        try:
            while True:  # Keep processing until no elements are left
                # Read 0th index of list:
                event_data = self.redis_service.lindex(list_key)
                if event_data:
                    await self._process_event(event_data.decode())

                    # Cleanup: remove the element from the list and delete the lock if successfully processed
                    if self.redis_service.pop_first_list_element(list_key):
                        logger.debug(
                            "Removed processed element from list: {}", list_key
                        )
                    else:
                        logger.warning(
                            "Tried to pop list element from: {}, but already removed from list?",
                            list_key,
                        )
                else:
                    # If no data is found, the list is empty, exit the loop
                    logger.debug(
                        "No more data found for event key: {}, exiting.", list_key
                    )
                    break
        except Exception:
            logger.exception("Could not process list key {}", list_key)
            raise

    async def _process_event(self, event_json: str) -> None:
        """
        Processes an individual ACA-Py event, transforming it to our CloudAPI format and saving/broadcasting to redis

        Args:
            event_json: The JSON string representation of the ACA-Py event.
        """
        event = parse_json_with_error_handling(AcaPyRedisEvent, event_json, logger)

        metadata_origin = event.metadata.origin

        if metadata_origin:
            origin = metadata_origin.lower()
        else:
            logger.warning("webhook event has unknown origin: {}", event)
            origin = "unknown"

        group_id = event.metadata.group_id
        wallet_id = event.metadata.x_wallet_id or origin

        acapy_topic = event.payload.category or event.payload.topic
        # category is the original acapy_topic as we used to received over http

        payload = event.payload.payload

        obfuscated_payload = self._obfuscate_sensitive_data(
            acapy_topic=acapy_topic, payload=payload
        )

        bound_logger = logger.bind(
            body={
                "wallet_id": wallet_id,
                "acapy_topic": acapy_topic,
                "origin": origin,
                "group_id": group_id,
                "payload": obfuscated_payload,
            }
        )
        bound_logger.debug("Processing ACA-Py Redis webhook event")

        # Map from the acapy webhook topic to a unified cloud api topic
        cloudapi_topic = topic_mapping.get(acapy_topic)
        if not cloudapi_topic:
            bound_logger.warning(
                "Not processing webhook event for acapy_topic `{}` as it doesn't exist in the topic_mapping",
                acapy_topic,
            )
            return

        acapy_webhook_event = AcaPyWebhookEvent(
            payload=payload,
            wallet_id=wallet_id,
            acapy_topic=acapy_topic,
            topic=cloudapi_topic,
            group_id=group_id,
            origin=origin,
        )

        cloudapi_webhook_event = acapy_to_cloudapi_event(acapy_webhook_event)
        if not cloudapi_webhook_event:
            bound_logger.warning(
                "Not processing webhook event for topic `{}` as no transformer exists for the topic",
                cloudapi_topic,
            )
            return

        webhook_event_json = cloudapi_webhook_event.model_dump_json()
        # Check if this webhook event should be forwarded to the Endorser service
        if (
            wallet_id == GOVERNANCE_LABEL  # represents event for the governance agent
            and cloudapi_topic == "endorsements"
            and payload_is_applicable_for_endorser(payload, logger=bound_logger)
        ):
            logger.debug("Forwarding endorsement event for Endorser service")
            transaction_id = payload["transaction_id"]  # check has asserted key exists
            self.redis_service.add_endorsement_event(
                event_json=webhook_event_json, transaction_id=transaction_id
            )
            await self.publish_endorsement_to_nats(transaction_id, webhook_event_json)

        # Check if event is billable, and get operation_type if it is an endorsement event
        is_billable, operation_type = is_applicable_for_billing(
            wallet_id=wallet_id,
            group_id=group_id,
            topic=cloudapi_topic,
            payload=payload,
            logger=bound_logger,
        )

        if is_billable:
            bound_logger.debug(
                "Forwarding billing event for Billing service",
            )
            if cloudapi_topic == "endorsements":
                # Add the operation type to the payload for endorsements
                # Simplifies the billing service's logic for determining the operation type
                endorse_event: Dict[str, Any] = orjson.loads(webhook_event_json)
                endorse_event["payload"]["type"] = operation_type
                webhook_event_for_billing = orjson.dumps(endorse_event)

            else:
                webhook_event_for_billing = webhook_event_json

            self.redis_service.add_billing_event(
                event_json=webhook_event_for_billing,
                group_id=group_id,
                wallet_id=wallet_id,
                timestamp_ns=event.metadata.time_ns,
            )

        # Add data to redis, which publishes to a redis pubsub channel that SseManager listens to
        self.redis_service.add_cloudapi_webhook_event(
            event_json=webhook_event_json,
            group_id=group_id,
            wallet_id=wallet_id,
            timestamp_ns=event.metadata.time_ns,
        )

        bound_logger.trace("Successfully processed ACA-Py Redis webhook event.")

    def _handle_unprocessable_event(self, key: str, error: Exception) -> None:
        """
        Handles an event that could not be processed successfully. The unprocessable event is persisted
        to a separate key for further investigation.

        Args:
            key: The Redis key where the problematic event was found.
            error: The exception that occurred during event processing.
        """
        logger.warning("Handling problematic event at key: {}", key)
        problematic_event = self.redis_service.pop_first_list_element(key)

        unprocessable_key = f"unprocessable:{key}:{uuid4().hex}"
        error_message = f"Could not process: {problematic_event}. Error: {error}"

        logger.warning(
            "Saving record of problematic event at key: {}. Error: `{}`",
            unprocessable_key,
            error_message,
        )
        self.redis_service.set(key=unprocessable_key, value=error_message)

    def _obfuscate_sensitive_data(
        self, acapy_topic: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        if acapy_topic == "endorse_transaction":
            return obfuscate_primary_data_in_payload(payload, logger)

        if acapy_topic == "issue_credential_v2_0_indy":
            if (
                "cred_request_metadata" in payload
                and "master_secret_blinding_data" in payload["cred_request_metadata"]
            ):
                obfuscated_payload = payload.copy()
                master_secret_blinding_data = obfuscated_payload[
                    "cred_request_metadata"
                ]["master_secret_blinding_data"]

                if "v_prime" in master_secret_blinding_data:
                    master_secret_blinding_data["v_prime"] = "REDACTED"

                if "vr_prime" in master_secret_blinding_data:
                    master_secret_blinding_data["vr_prime"] = "REDACTED"

                return obfuscated_payload

        # No modification:
        return payload

    async def publish_endorsement_to_nats(
        self, transaction_id: str, event: str
    ) -> None:
        """
        Publishes an endorsement event to the NATS server.

        Args:
            event: The endorsement event to publish.
        """
        logger.debug("Publishing endorsement event to NATS")
        try:
            ack = await self.jetstream.publish(
                f"cloudapi.aries.events.endorser.{transaction_id}", event.encode()
            )
            if not ack:
                logger.error("Error publishing endorsement event to NATS: {}", ack)
                raise Exception("Error publishing endorsement event to NATS")
        except (ErrConnectionClosed, ErrTimeout, ErrNoServers) as e:
            logger.error("Error publishing endorsement event to NATS: {}", e)
            raise e

    async def start_nats_client(self) -> None:
        """
        Starts the NATS client for the endorsement processor.
        """
        logger.info("Starting NATS client")
        try:
            connect_kwargs = {
                "servers": [NATS_SERVER],
            }
            if NATS_CREDS_FILE:
                connect_kwargs["user_credentials"] = NATS_CREDS_FILE
            else:
                logger.warning(
                    "No NATS credentials file found, assuming local development"
                )
            self.nats_client: NATS = await nats.connect(**connect_kwargs)

        except (ErrConnectionClosed, ErrTimeout, ErrNoServers) as e:
            logger.error("Error connecting to NATS server: {}", e)
            raise e
        logger.debug("Connected to NATS server")

        self.jetstream: JetStreamContext = self.nats_client.jetstream()
