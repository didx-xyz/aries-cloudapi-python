import asyncio
import datetime
import sys
from typing import List, NoReturn

from aries_cloudcontroller import AcaPyClient

from endorser.util.endorsement import accept_endorsement, should_accept_endorsement
from shared.constants import (
    GOVERNANCE_AGENT_API_KEY,
    GOVERNANCE_AGENT_URL,
    GOVERNANCE_LABEL,
)
from shared.log_config import get_logger
from shared.models.endorsement import Endorsement
from shared.models.webhook_events.payloads import CloudApiWebhookEventGeneric
from shared.services.redis_service import RedisService
from shared.util.rich_parsing import parse_json_with_error_handling

logger = get_logger(__name__)


class EndorsementProcessor:
    """
    Class to process endorsement webhook events that the Webhooks service writes to `endorsement_redis_prefix`
    """

    def __init__(self, redis_service: RedisService) -> None:
        self.redis_service = redis_service
        self._new_event_notification = asyncio.Event()

        self.endorse_prefix = self.redis_service.endorsement_redis_prefix

        self._pubsub = None  # for managing redis pubsub connection
        self._pubsub_thread = None

        self._tasks: List[asyncio.Task] = []  # To keep track of running tasks

    def start(self) -> None:
        """
        Starts the background tasks for processing endorsement events.
        """
        # self._start_notification_listener()  # disable as it is currently unused
        self._tasks.append(
            asyncio.create_task(
                self._process_endorsement_requests(), name="Process endorsements"
            )
        )
        logger.info("Endorsement processing started.")

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
            logger.info("Stopped Endorsement pubsub thread")

        if self._pubsub:
            await asyncio.sleep(0.1)  # allow thread to stop before disconnecting
            self._pubsub.disconnect()
            logger.info("Disconnected Endorsement pubsub instance")
        logger.info("Endorsement processing stopped.")

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

    def _set_notification_handler(self, msg) -> None:
        """
        Processing handler for when set notifications are received
        """
        if f"{self.endorse_prefix}:" in msg["data"].decode():
            logger.trace("Received endorse set notification: {}", msg)
            self._new_event_notification.set()

    def _start_notification_listener(self) -> None:
        """
        Listens for keyspace notifications related to endorsements and sets an event to resume processing.
        """
        self._pubsub = self.redis_service.redis.pubsub()

        # Subscribe this pubsub channel to the notification pattern (set may represent endorsement events)
        notification_pattern = "__keyevent@0__:set"
        self._pubsub.psubscribe(
            **{notification_pattern: self._set_notification_handler}
        )
        self._pubsub_thread = self._pubsub.run_in_thread(sleep_time=0.01)

        logger.info("Notification listener subscribed to redis keyspace notifications")

    async def _process_endorsement_requests(self) -> NoReturn:
        """
        Processing handler for incoming endorsement events
        """
        logger.info("Starting endorsement processor")

        exception_count = 0
        max_exception_count = 5  # break inf loop after 5 consecutive exceptions

        attempts_without_events = 0
        max_attempts_without_events = sys.maxsize  # use max int to never stop
        sleep_duration = 0.1

        while True:
            try:
                batch_keys = self.redis_service.scan_keys(
                    match_pattern=f"{self.endorse_prefix}:*", count=5000
                )
                if batch_keys:
                    attempts_without_events = 0  # Reset the counter
                    for key in batch_keys:
                        await self._attempt_process_endorsement(key)

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
                        logger.info("Keyspace notification triggered")
                        self._new_event_notification.clear()  # Reset the event for the next wait
                        attempts_without_events = 0  # Reset the counter
                    else:
                        await asyncio.sleep(sleep_duration)  # prevent a busy loop
                exception_count = 0  # reset exception count after successful loop
            except Exception:  # pylint: disable=W0718
                exception_count += 1
                logger.exception(
                    "Something went wrong while processing endorsement events. Continuing..."
                )
                if exception_count >= max_exception_count:
                    raise  # exit inf loop

    async def _attempt_process_endorsement(self, event_key: str) -> None:
        """
        Attempts to process an endorsement event from Redis, ensuring that only one instance
        processes the event at a time by acquiring a lock.

        Args:
            list_key: The Redis key of the list to process.
        """
        logger.trace("Attempt process: {}", event_key)
        lock_key = f"lock:{event_key}"
        extend_lock_task = None

        lock_duration = 1  # second

        if self.redis_service.set_lock(
            key=lock_key,
            px=lock_duration * 1000,  # to milliseconds
        ):
            logger.trace("Successfully set lock for {}", event_key)
            event_json = self.redis_service.get(event_key)
            if not event_json:
                logger.warning(
                    "Tried to read an event from key {}, but event has been deleted:",
                    event_key,
                )
                return

            try:
                # Start a background task to extend the lock periodically
                extend_lock_task = self.redis_service.extend_lock_task(
                    lock_key, interval=datetime.timedelta(seconds=lock_duration)
                )

                await self._process_endorsement_event(event_json)
                if self.redis_service.delete_key(event_key):
                    logger.info("Deleted processed endorsement event: {}", event_key)
                else:
                    logger.warning(
                        "Couldn't delete processed endorsement event: {}", event_key
                    )
            except Exception as e:  # pylint: disable=W0718
                # if this particular event is unprocessable, we should remove it from the inputs, to avoid deadlocking
                logger.error("Processing {} raised an exception: {}", event_key, e)
                self._handle_unprocessable_endorse_event(event_key, event_json, e)
            finally:
                # Cancel the lock extension task if it's still running
                if extend_lock_task:
                    extend_lock_task.cancel()
        else:
            logger.debug(
                "Event {} is currently being processed by another instance.", event_key
            )

    async def _process_endorsement_event(self, event_json: str) -> None:
        """
        Processes an individual endorsement event, evaluating if it should be accepted and then endorsing as governance

        Args:
            event_json: The JSON string representation of the endorsement event.
        """
        event = parse_json_with_error_handling(
            CloudApiWebhookEventGeneric, event_json, logger
        )
        logger.debug("Processing endorsement event for agent `{}`", event.origin)

        # We're only interested in events from the governance agent
        if event.wallet_id != GOVERNANCE_LABEL:
            logger.warning("Endorsement request is not for governance agent.")
            return

        endorsement = Endorsement(**event.payload)

        async with AcaPyClient(
            base_url=GOVERNANCE_AGENT_URL, api_key=GOVERNANCE_AGENT_API_KEY
        ) as client:
            # Check if endorsement request is indeed applicable
            if not await should_accept_endorsement(client, endorsement):
                logger.info(  # check already logged the reason as warning
                    "Endorsement request with transaction id `{}` is not applicable for endorsement.",
                    endorsement.transaction_id,
                )
                return

            logger.info(
                "Endorsement request with transaction id `{}` is applicable for endorsement, accepting request.",
                endorsement.transaction_id,
            )
            await accept_endorsement(client, endorsement)

    def _handle_unprocessable_endorse_event(
        self, key: str, event_json: str, error: Exception
    ) -> None:
        """
        Handles an event that could not be processed successfully. The unprocessable event is persisted
        to a separate key for further investigation.

        Args:
            key: The Redis key where the problematic event was found.
            error: The exception that occurred during event processing.
        """
        bound_logger = logger.bind(body={"key": key})
        bound_logger.warning("Handling problematic endorsement event")

        unprocessable_key = f"unprocessable:{key}"
        error_message = f"Could not process: {event_json}. Error: {error}"

        bound_logger.info(
            "Saving record of problematic event at key: {}. Error: `{}`",
            unprocessable_key,
            error_message,
        )
        self.redis_service.set(key=unprocessable_key, value=error_message)

        bound_logger.info("Deleting original problematic event")
        self.redis_service.delete_key(key=key)
        bound_logger.info("Successfully handled unprocessable event.")

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

    async def _subscribe(self) -> JetStreamContext.PullSubscription:
        """
        Subscribes to the NATS subject for endorsement events.
        """
        logger.info("Subscribing to NATS subject: cloudapi.aries.events.endorser.>")
        try:
            subscribe_kwargs = {
                "durable": ENDORSER_DURABLE_CONSUMER,
                "subject": f"{NATS_SUBJECT}.endorser.>",
                "stream": NATS_STREAM,
            }
            subscription = await self.jetstream.pull_subscribe(**subscribe_kwargs)
        except (BadSubscriptionError, Error) as e:
            logger.error("Error subscribing to NATS subject: {}", e)
            raise e
        except Exception as e:
            logger.error("Unknown error subscribing to NATS subject: {}", e)
            raise e
        logger.debug("Subscribed to NATS subject")

        return subscription
