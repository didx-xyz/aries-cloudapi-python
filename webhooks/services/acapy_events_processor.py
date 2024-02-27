import asyncio
from typing import NoReturn, Optional, Set

from shared import APIRouter
from shared.log_config import get_logger
from shared.models.webhook_topics import (
    AcaPyWebhookEvent,
    CloudApiWebhookEvent,
    topic_mapping,
)
from shared.models.webhook_topics.base import AcaPyRedisEvent
from shared.util.rich_parsing import parse_with_error_handling
from webhooks.models import acapy_to_cloudapi_event
from webhooks.services.redis_service import RedisService

logger = get_logger(__name__)

router = APIRouter()


class AcapyEventsProcessor:
    """
    Class to process ACA-Py webhook events that the plugin writes to redis.
    """

    def __init__(self, redis_service: RedisService) -> None:
        self.redis_service = redis_service

        # Redis prefix for acapy events:
        self.acapy_redis_prefix = self.redis_service.acapy_redis_prefix

        # Event for indicating redis keyspace notifications
        self._new_event_notification = asyncio.Event()

        self._start_background_tasks()

    def _start_background_tasks(self) -> None:
        """
        Start the background tasks as part of AcapyEventsProcessor's lifecycle
        """
        asyncio.create_task(self._notification_listener())
        asyncio.create_task(self._process_incoming_events())

    def _rpush_notification_handler(self, msg):
        """
        Processing handler for when rpush notifications are received
        """
        logger.trace(f"Received rpush notification: {msg}")
        self._new_event_notification.set()

    async def _notification_listener(self):
        """
        Listens for keyspace notifications from Redis and sets an event to resume processing.
        """
        # Example subscription pattern for keyspace notifications. Adjust as necessary.
        pubsub = self.redis_service.redis.pubsub()

        # Subscribe this pubsub channel to the notification pattern (rpush represents ACA-Py writing to list types)
        notification_pattern = "__keyevent@0__:rpush"
        pubsub.psubscribe(**{notification_pattern: self._rpush_notification_handler})
        pubsub.run_in_thread(sleep_time=0.01)

        logger.info(f"Notification listener subscribed to redis keyspace notifications")

    async def _process_incoming_events(self) -> NoReturn:
        logger.info("Starting ACA-Py Events Processor")
        while True:
            batch_event_keys = self._scan_acapy_event_keys()
            for list_key in batch_event_keys:  # the keys are of LIST type
                self._attempt_process_list_events(list_key)
            await asyncio.sleep(1)  # sleep to prevent busy loop
            # here we can sleep until keyspace notification

    def _scan_acapy_event_keys(self) -> Set[str]:
        collected_keys = set()
        cursor = 0  # Starting cursor value for SCAN
        logger.debug("Starting SCAN to fetch incoming ACA-Py event keys from Redis.")

        try:
            while True:  # Loop until the cursor returned by SCAN is '0'
                cursor, keys = self.redis_service.redis.scan(
                    cursor, match=self.redis_service.acapy_redis_prefix, count=1000
                )
                if keys:
                    keys_batch = set(key.decode("utf-8") for key in keys)
                    collected_keys.update(keys_batch)
                    logger.debug(
                        f"Fetched {len(keys_batch)} ACA-Py event keys from Redis. Cursor value: {cursor}"
                    )
                else:
                    logger.debug("No ACA-Py event keys found in this batch.")

                # Cluster scan returns dict of {node: cursor_value}
                if cursor == 0 or all(c == 0 for c in cursor.values()):
                    logger.debug(
                        f"Completed SCAN for ACA-Py event keys, fetched {len(collected_keys)} total."
                    )
                    break  # Exit the loop
        except Exception:
            logger.exception(
                "An exception occurred when fetching ACA-Py event keys from redis. Continuing..."
            )

        return collected_keys

    def _attempt_process_list_events(self, list_key: str) -> None:
        """
        Attempt to process an event, acquiring a lock to ensure it's processed once.
        """
        lock_key = f"lock:{list_key}"
        if self.redis_service.set_lock(lock_key, px=500):  # Lock for 500 ms
            self._process_list_events(list_key)

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

    def _process_list_events(self, list_key):
        try:
            while True:  # Keep processing until no elements are left
                # Read 0th index of list:
                event_data = self.redis_service.lindex(list_key)
                if event_data:
                    self._process_event(event_data)

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
        except Exception as e:
            logger.error(f"Could not load event data ({event_data}): {e}")

    def _process_event(self, event_json: str) -> bool:
        event = parse_with_error_handling(AcaPyRedisEvent, event_json)

        wallet_id = event.metadata.x_wallet_id

        acapy_topic = event.payload.category
        # I think category is the original acapy_topic. `topic` seems transformed

        origin = "multitenant"  # todo

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
                "Not processing webhook event for acapy_topic `{}` as it doesn't exist in the topic_mapping",
                acapy_topic,
            )
            return

        acapy_webhook_event = AcaPyWebhookEvent(
            payload=payload,
            wallet_id=wallet_id,
            acapy_topic=acapy_topic,
            topic=cloudapi_topic,
            origin=origin,
        )

        cloudapi_webhook_event: Optional[CloudApiWebhookEvent] = (
            acapy_to_cloudapi_event(acapy_webhook_event)
        )
        if not cloudapi_webhook_event:
            bound_logger.warning(
                "Not processing webhook event for topic `{}` as no transformer exists for the topic",
                cloudapi_topic,
            )
            return

        webhook_event_json = cloudapi_webhook_event.model_dump_json()

        # Add data to redis, which publishes to a redis pubsub channel that SseManager listens to
        self.redis_service.add_cloudapi_webhook_event(webhook_event_json, wallet_id)

        bound_logger.debug("Successfully processed ACA-Py Redis webhook event.")
