import asyncio
from typing import List, NoReturn

from aries_cloudcontroller import AcaPyClient
from nats.errors import BadSubscriptionError, Error, TimeoutError
from nats.js.client import JetStreamContext

from endorser.util.endorsement import accept_endorsement, should_accept_endorsement
from shared.constants import (
    ENDORSER_DURABLE_CONSUMER,
    GOVERNANCE_AGENT_API_KEY,
    GOVERNANCE_AGENT_URL,
    GOVERNANCE_LABEL,
    NATS_STREAM,
    NATS_SUBJECT,
)
from shared.log_config import get_logger
from shared.models.endorsement import Endorsement
from shared.models.webhook_events.payloads import CloudApiWebhookEventGeneric
from shared.util.rich_parsing import parse_json_with_error_handling

logger = get_logger(__name__)


class EndorsementProcessor:
    """
    Class to process endorsement webhook events that the Webhooks service writes to `endorsement_redis_prefix`
    """

    def __init__(self, jetstream: JetStreamContext) -> None:
        self.jetstream: JetStreamContext = jetstream

        self._tasks: List[asyncio.Task] = []  # To keep track of running tasks

    def start(self) -> None:
        """
        Starts the background tasks for processing endorsement events.
        """
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

        logger.info("Endorsement processing stopped.")

    def are_tasks_running(self) -> bool:
        """
        Checks if the background tasks are still running.

        Returns:
            True if all background tasks are running, False if any task has stopped.
        """
        logger.debug("Checking if all tasks are running")

        tasks_running = self._tasks and all(not task.done() for task in self._tasks)

        if not tasks_running:
            for task in self._tasks:
                if task.done():
                    logger.error("Task `{}` is not running", task.get_name())

        all_running = tasks_running

        logger.debug("All tasks running: {}", all_running)
        return all_running

    async def _process_endorsement_requests(self) -> NoReturn:
        subscription = await self._subscribe()
        while True:
            try:
                messages = await subscription.fetch(10, 1)
                for message in messages:
                    message_subject = message.subject
                    message_data = message.data.decode()
                    logger.trace(
                        "received message: {} with subject {}",
                        message_data,
                        message_subject,
                    )
                    await self._process_endorsement_event(message_data)
                    await message.ack()
            except TimeoutError:
                logger.trace("Timeout fetching messages continuing...")
                await asyncio.sleep(1)
            except Exception as e:  # pylint: disable=W0703
                logger.error("Error processing endorsement event: {}", e)
                await self._handle_unprocessable_endorse_event(
                    message_subject, message_data, e
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

    async def _handle_unprocessable_endorse_event(
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

        unprocessable_key = f"unprocessable.{key}"
        error_message = f"Could not process: {event_json}. Error: {error}"

        bound_logger.info(
            "Saving record of problematic event at key: {}. Error: `{}`",
            unprocessable_key,
            error_message,
        )
        await self.jetstream.publish(unprocessable_key, error_message.encode())
        bound_logger.info("Successfully handled unprocessable event.")

    async def _subscribe(self) -> JetStreamContext.PullSubscription:
        """
        Subscribes to the NATS subject for endorsement events.
        """
        logger.info(f"Subscribing to NATS subject: {NATS_SUBJECT}.endorser.*")
        try:
            subscribe_kwargs = {
                "subject": f"{NATS_SUBJECT}.endorser.*",
                "durable": ENDORSER_DURABLE_CONSUMER,
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
