import asyncio
from typing import List, NoReturn

from aries_cloudcontroller import AcaPyClient

from endorser.util.endorsement import accept_endorsement, should_accept_endorsement
from shared.constants import GOVERNANCE_AGENT_API_KEY, GOVERNANCE_AGENT_URL
from shared.log_config import get_logger
from shared.models.webhook_topics.base import CloudApiWebhookEvent, Endorsement
from shared.services.redis_service import RedisService
from shared.util.rich_parsing import parse_with_error_handling

logger = get_logger(__name__)


class EndorsementProcessor:
    def __init__(self, redis_service: RedisService) -> None:
        self.redis_service = redis_service
        self._new_event_notification = asyncio.Event()

        self.endorse_prefix = self.redis_service.endorsement_redis_prefix

        self._tasks: List[asyncio.Task] = []  # To keep track of running tasks

    def start(self):
        """
        Starts the background tasks for processing endorsement events.
        """
        self._start_notification_listener()
        self._tasks.append(asyncio.create_task(self._process_endorsement_requests()))
        logger.info("Endorsement processing started.")

    async def stop(self):
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
        logger.info("Endorsement processing stopped.")

    def are_tasks_running(self) -> bool:
        """
        Checks if the background tasks are still running.

        Returns:
            True if all background tasks are running, False if any task has stopped.
        """
        return all(not task.done() for task in self._tasks)

    def _set_notification_handler(self, msg) -> None:
        """
        Processing handler for when set notifications are received
        """
        if f"{self.endorse_prefix}:" in msg:
            logger.trace(f"Received endorse set notification: {msg}")
            self._new_event_notification.set()

    def _start_notification_listener(self) -> None:
        """
        Listens for keyspace notifications related to endorsements and sets an event to resume processing.
        """
        pubsub = self.redis_service.redis.pubsub()

        # Subscribe this pubsub channel to the notification pattern (set may represent endorsement events)
        notification_pattern = "__keyevent@0__:set"
        pubsub.psubscribe(**{notification_pattern: self._set_notification_handler})
        pubsub.run_in_thread(sleep_time=0.01)

        logger.info("Notification listener subscribed to redis keyspace notifications")

    async def _process_endorsement_requests(self) -> NoReturn:
        """
        Processing handler for incoming endorsement events
        """
        logger.info("Starting endorsement processor")

        attempts_without_events = 0
        max_attempts_without_events = 500
        sleep_duration = 0.02

        while True:
            try:
                batch_keys = self.redis_service.scan_keys(
                    match_pattern=f"{self.endorse_prefix}:*", count=10000
                )
                if batch_keys:
                    attempts_without_events = 0  # Reset the counter
                    for key in batch_keys:
                        self._attempt_process_endorsement(key)

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
                    "Something went wrong while processing endorsement events. Continuing..."
                )

    def _attempt_process_endorsement(self, event_key: str) -> None:
        """
        Attempts to process an endorsement event from Redis, ensuring that only one instance
        processes the event at a time by acquiring a lock.

        Args:
            list_key: The Redis key of the list to process.
        """
        lock_key = f"lock:{event_key}"
        if self.redis_service.set_lock(lock_key, px=500):  # Lock for 500 ms
            try:
                event_json = self.redis_service.get(event_key)
                self._process_endorsement_event(event_json)
                if self.redis_service.delete_key(event_key):
                    logger.info(f"Deleted processed endorsement event: {event_key}")
                else:
                    logger.warning(
                        f"Couldn't delete processed endorsement event: {event_key}"
                    )
            except Exception:
                logger.exception(
                    "Something went wrong with processing endorsement. Continuing ..."
                )
                # todo:
                # if this particular event is unprocessable, we should remove it from the inputs, to avoid deadlocking
                # self._handle_unprocessable_event(event_key, e)
            finally:
                # Delete lock after processing, whether it completed or errored:
                if self.redis_service.delete_key(lock_key):
                    logger.debug(f"Deleted lock key: {lock_key}")
                else:
                    logger.warning(
                        f"Could not delete lock key: {lock_key}. Perhaps it expired?"
                    )
        else:
            logger.debug(
                f"Event {event_key} is currently being processed by another instance."
            )

    async def _process_endorsement_event(self, event_json: str):
        event: CloudApiWebhookEvent = parse_with_error_handling(
            CloudApiWebhookEvent, event_json
        )
        logger.debug(
            "Processing endorsement event for agent `{}` and wallet `{}`",
            event.origin,
            event.wallet_id,
        )
        # We're only interested in events from the governance agent
        if event.origin != "governance":
            logger.warning("Endorsement request is not for governance agent.")
            return

        endorsement = Endorsement(**event.payload)

        async with AcaPyClient(
            base_url=GOVERNANCE_AGENT_URL, api_key=GOVERNANCE_AGENT_API_KEY
        ) as client:
            # Not interested in this endorsement request
            if not await should_accept_endorsement(client, endorsement):
                logger.warning(
                    "Endorsement request with transaction id `{}` is not applicable for endorsement.",
                    endorsement.transaction_id,
                )
                return

            logger.info(
                "Endorsement request with transaction id `{}` is applicable for endorsement, accepting request.",
                endorsement.transaction_id,
            )
            await accept_endorsement(client, endorsement)
