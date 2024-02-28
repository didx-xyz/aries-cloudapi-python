import asyncio
from typing import NoReturn, Set
from uuid import uuid4

from shared import APIRouter
from shared.log_config import get_logger
from shared.models.webhook_topics import AcaPyWebhookEvent, topic_mapping
from shared.models.webhook_topics.base import AcaPyRedisEvent
from shared.util.rich_parsing import parse_with_error_handling
from webhooks.models import acapy_to_cloudapi_event
from webhooks.services.webhooks_redis_serivce import WebhooksRedisService

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

        self._start_background_tasks()

    def _start_background_tasks(self) -> None:
        """
        Start the background tasks as part of AcaPyEventsProcessor's lifecycle
        """
        asyncio.create_task(self._notification_listener())
        asyncio.create_task(self._process_incoming_events())

    def _rpush_notification_handler(self, msg) -> None:
        """
        Processing handler for when rpush notifications are received
        """
        logger.trace(f"Received rpush notification: {msg}")
        self._new_event_notification.set()

    async def _notification_listener(self) -> None:
        """
        Listens for keyspace notifications from Redis and sets an event to resume processing.
        """
        # Example subscription pattern for keyspace notifications. Adjust as necessary.
        pubsub = self.redis_service.redis.pubsub()

        # Subscribe this pubsub channel to the notification pattern (rpush represents ACA-Py writing to list types)
        notification_pattern = "__keyevent@0__:rpush"
        pubsub.psubscribe(**{notification_pattern: self._rpush_notification_handler})
        pubsub.run_in_thread(sleep_time=0.01)

        logger.info("Notification listener subscribed to redis keyspace notifications")

    async def _process_incoming_events(self) -> NoReturn:
        """
        Processing handler for incoming ACA-Py redis webhooks events
        """
        logger.info("Starting ACA-Py Events Processor")

        attempts_without_events = 0
        max_attempts_without_events = 1000
        sleep_duration = 0.02

        while True:
            try:
                batch_event_keys = self._scan_acapy_event_keys()
                if batch_event_keys:
                    attempts_without_events = 0  # Reset the counter
                    for list_key in batch_event_keys:  # the keys are of LIST type
                        self._attempt_process_list_events(list_key)

                else:
                    attempts_without_events += 1
                    if attempts_without_events >= max_attempts_without_events:
                        # Wait for a keyspace notification before continuing
                        logger.debug(
                            f"Scan has returned no keys {max_attempts_without_events} times in a row. "
                            "Waiting for keyspace notification..."
                        )
                        await self._new_event_notification.wait()
                        logger.info("Keyspace notification triggered")
                        self._new_event_notification.clear()  # Reset the event for the next wait
                        attempts_without_events = 0  # Reset the counter
                    else:
                        await asyncio.sleep(sleep_duration)  # prevent a busy loop
            except Exception:
                logger.exception(
                    "Something went wrong while processing incoming events. Continuing..."
                )

    def _scan_acapy_event_keys(self) -> Set[str]:
        """
        Scans Redis for keys matching the ACA-Py event prefix and returns a set of these keys.

        Returns:
            A set of Redis keys that match the ACA-Py event prefix.
        """
        collected_keys = set()
        logger.trace("Starting SCAN to fetch incoming ACA-Py event keys from Redis.")

        try:
            _, keys = self.redis_service.redis.scan(
                cursor=0, match=self.acapy_redis_prefix, count=10000
            )
            if keys:
                collected_keys = set(key.decode("utf-8") for key in keys)
                logger.debug(f"Fetched {len(collected_keys)} event keys from Redis")
            else:
                logger.trace("No ACA-Py event keys found in this batch.")
        except Exception:
            logger.exception(
                "An exception occurred when fetching ACA-Py event keys from redis. Continuing..."
            )

        return collected_keys

    def _attempt_process_list_events(self, list_key: str) -> None:
        """
        Attempts to process a list-based event in Redis, ensuring that only one instance processes
        the event at a time by acquiring a lock.

        Args:
            list_key: The Redis key of the list to process.
        """
        lock_key = f"lock:{list_key}"
        if self.redis_service.set_lock(lock_key, px=500):  # Lock for 500 ms
            try:
                self._process_list_events(list_key)
            except Exception as e:
                # if this particular event is unprocessable, we should remove it from the inputs, to avoid deadlocking
                self._handle_unprocessable_event(list_key, e)
            finally:
                # Delete lock after processing list, whether it completed or errored:
                if self.redis_service.delete_key(lock_key):
                    logger.debug(f"Deleted lock key: {lock_key}")
                else:
                    logger.warning(
                        f"Could not delete lock key: {lock_key}. Perhaps it expired?"
                    )
        else:
            logger.debug(
                f"Event {list_key} is currently being processed by another instance."
            )

    def _process_list_events(self, list_key) -> None:
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
                    self._process_event(event_data.decode())

                    # Cleanup: remove the element from the list and delete the lock if successfully processed
                    if self.redis_service.pop_first_list_element(list_key):
                        logger.debug(f"Removed processed element from list: {list_key}")
                    else:
                        logger.warning(
                            f"Tried to pop list element from: {list_key}, but already removed from list?"
                        )
                else:
                    # If no data is found, the list is empty, exit the loop
                    logger.debug(
                        f"No more data found for event key: {list_key}, exiting."
                    )
                    break
        except Exception:
            logger.exception(f"Could not load event data ({event_data})")
            raise

    def _process_event(self, event_json: str) -> None:
        """
        Processes an individual ACA-Py event, transforming it to our CloudAPI format and saving/broadcasting to redis

        Args:
            event_json: The JSON string representation of the ACA-Py event.
        """
        event = parse_with_error_handling(AcaPyRedisEvent, event_json)

        wallet_id = event.metadata.x_wallet_id or "admin"
        origin = "multitenant" if event.metadata.x_wallet_id else "governance"

        acapy_topic = event.payload.category or event.payload.topic
        # I think category is the original acapy_topic. `topic` seems transformed

        payload = event.payload.payload

        bound_logger = logger.bind(
            body={
                "wallet_id": wallet_id,
                "acapy_topic": acapy_topic,
                "origin": origin,
                "payload": payload,
            }
        )
        bound_logger.debug("Processing ACA-Py Redis webhook event")

        # Map from the acapy webhook topic to a unified cloud api topic
        cloudapi_topic = topic_mapping.get(acapy_topic)
        if not cloudapi_topic:
            bound_logger.warning(
                f"Not processing webhook event for acapy_topic `{acapy_topic}` as it doesn't exist in the topic_mapping",
            )
            return

        acapy_webhook_event = AcaPyWebhookEvent(
            payload=payload,
            wallet_id=wallet_id,
            acapy_topic=acapy_topic,
            topic=cloudapi_topic,
            origin=origin,
        )

        cloudapi_webhook_event = acapy_to_cloudapi_event(acapy_webhook_event)
        if not cloudapi_webhook_event:
            bound_logger.warning(
                f"Not processing webhook event for topic `{cloudapi_topic}` as no transformer exists for the topic",
            )
            return

        webhook_event_json = cloudapi_webhook_event.model_dump_json()

        # Add data to redis, which publishes to a redis pubsub channel that SseManager listens to
        self.redis_service.add_cloudapi_webhook_event(webhook_event_json, wallet_id)

        bound_logger.debug("Successfully processed ACA-Py Redis webhook event.")

    def _handle_unprocessable_event(self, key: str, error: Exception) -> None:
        """
        Handles an event that could not be processed successfully. The unprocessable event is persisted
        to a separate key for further investigation.

        Args:
            key: The Redis key where the problematic event was found.
            error: The exception that occurred during event processing.
        """
        logger.warning(f"Handling problematic event at key: {key}")
        problematic_event = self.redis_service.pop_first_list_element(key)

        unprocessable_key = f"unprocessable:{key}:{uuid4().hex}"
        error_message = f"Could not process: {problematic_event}. Error: {error}"

        logger.warning(
            f"Saving record of problematic event at key: {unprocessable_key}. Error: `{error_message}`"
        )
        self.redis_service.set(key=unprocessable_key, value=error_message)
