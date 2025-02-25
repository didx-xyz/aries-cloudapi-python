import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional

import orjson
from nats.errors import BadSubscriptionError, Error, TimeoutError
from nats.js.api import ConsumerConfig, DeliverPolicy
from nats.js.client import JetStreamContext
from nats.js.errors import FetchTimeoutError
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_never,
    wait_exponential,
)

from shared.constants import (
    NATS_STATE_STREAM,
    NATS_STATE_SUBJECT,
    SSE_LOOK_BACK,
    SSE_TIMEOUT,
)
from shared.log_config import get_logger
from shared.models.webhook_events import CloudApiWebhookEventGeneric

logger = get_logger(__name__)


class NatsEventsProcessor:
    """
    Class to handle processing of NATS events. Calling the process_events method will
    subscribe to the NATS server and return an async generator that will yield events
    """

    def __init__(self, jetstream: JetStreamContext):
        self.js_context: JetStreamContext = jetstream

    async def _subscribe(
        self,
        *,
        group_id: Optional[str] = None,
        wallet_id: str,
        topic: str,
        state: str,
        start_time: str,
        state_uuid: uuid.UUID,
    ) -> JetStreamContext.PullSubscription:
        bound_logger = logger.bind(
            body={
                "wallet_id": wallet_id,
                "group_id": group_id,
                "topic": topic,
                "state": state,
                "start_time": start_time,
                "uuid": state_uuid,
            }
        )

        group_id = group_id or "*"
        subscribe_kwargs = {
            "subject": f"{NATS_STATE_SUBJECT}.{group_id}.{wallet_id}.{topic}.{state}",
            "stream": NATS_STATE_STREAM,
        }

        config = ConsumerConfig(
            deliver_policy=DeliverPolicy.BY_START_TIME,
            opt_start_time=start_time,
        )

        def _retry_log(retry_state: RetryCallState):
            """Custom logging for retry attempts."""
            if retry_state.outcome.failed:
                exception = retry_state.outcome.exception()
                bound_logger.warning(
                    "Retry attempt {} failed due to {}: {}",
                    retry_state.attempt_number,
                    type(exception).__name__,
                    exception,
                )

        # This is a custom retry decorator that will retry on TimeoutError
        # and wait exponentially up to a max of 16 seconds between retries indefinitely
        @retry(
            retry=retry_if_exception_type(TimeoutError),
            wait=wait_exponential(multiplier=1, max=16),
            after=_retry_log,
            stop=stop_never,
        )
        async def pull_subscribe():
            try:
                bound_logger.trace("Attempting to subscribe to JetStream")
                subscription = await self.js_context.pull_subscribe(
                    config=config, **subscribe_kwargs
                )

                # Get consumer info to verify that the subscription was successful
                # TODO test if this is necessary/helps
                await subscription.consumer_info()

                bound_logger.debug("Successfully subscribed to JetStream")
                return subscription
            except BadSubscriptionError as e:
                bound_logger.error("BadSubscriptionError subscribing to NATS: {}", e)
                raise
            except Error as e:
                bound_logger.error("Error subscribing to NATS: {}", e)
                raise

        try:
            return await pull_subscribe()
        except Exception:
            bound_logger.exception("An exception occurred subscribing to NATS")
            raise

    @asynccontextmanager
    async def process_events(
        self,
        *,
        group_id: Optional[str] = None,
        wallet_id: str,
        topic: str,
        state: str,
        stop_event: asyncio.Event,
        duration: Optional[int] = None,
        look_back: Optional[int] = None,
    ):
        duration = duration or SSE_TIMEOUT
        look_back = look_back or SSE_LOOK_BACK
        state_uuid = uuid.uuid4()
        bound_logger = logger.bind(
            body={
                "wallet_id": wallet_id,
                "group_id": group_id,
                "topic": topic,
                "state": state,
                "duration": duration,
                "look_back": look_back,
                "uuid": state_uuid,
            }
        )
        bound_logger.debug("Processing events")

        # Get the current time
        current_time = datetime.now()

        # Subtract look_back time from the current time
        look_back_time = current_time - timedelta(seconds=look_back)

        # Format the time in the required format
        start_time = look_back_time.isoformat(timespec="milliseconds") + "Z"

        async def event_generator(*, subscription: JetStreamContext.PullSubscription):
            try:
                nr_of_timeout_errors = 0
                end_time = time.time() + duration
                while not stop_event.is_set():
                    remaining_time = end_time - time.time()
                    bound_logger.trace("Remaining time: {}", remaining_time)
                    if remaining_time <= 0:
                        bound_logger.debug("Timeout reached")
                        stop_event.set()
                        break

                    try:
                        messages = await subscription.fetch(
                            batch=5, timeout=0.5, heartbeat=0.05
                        )
                        for message in messages:
                            event = orjson.loads(message.data)
                            bound_logger.trace("Received event: {}", event)
                            yield CloudApiWebhookEventGeneric(**event)
                            await message.ack()

                    except FetchTimeoutError:
                        # Fetch timeout, continue
                        bound_logger.debug("Timeout fetching messages continuing...")
                        await asyncio.sleep(0.1)

                    except TimeoutError:
                        bound_logger.error("<><><>TimeoutError<><><>")
                        if nr_of_timeout_errors == 5:
                            bound_logger.warning(
                                "Subscription lost connection, attempting to resubscribe..."
                            )
                            try:
                                await subscription.unsubscribe()
                                bound_logger.debug("Unsubscribed.")
                            except BadSubscriptionError as e:
                                bound_logger.warning(
                                    "BadSubscriptionError unsubscribing from NATS after subscription lost: {}",
                                    e,
                                )

                            subscription = await self._subscribe(
                                group_id=group_id,
                                wallet_id=wallet_id,
                                topic=topic,
                                state=state,
                                start_time=start_time,
                                state_uuid=state_uuid,
                            )
                            bound_logger.debug("Successfully resubscribed to NATS.")
                            nr_of_timeout_errors = 0

                            continue

                        bound_logger.debug("TimeoutError, retrying...")
                        nr_of_timeout_errors += 1
                        await asyncio.sleep(0.1)

                    except Error as e:
                        bound_logger.error("Nats error in event generator: {}", e)
                        stop_event.set()
                        raise

                    except Exception:  # pylint: disable=W0718
                        bound_logger.exception("Unexpected error in event generator")
                        stop_event.set()
                        raise

            except asyncio.CancelledError:
                bound_logger.debug("Event generator cancelled")
                stop_event.set()

            finally:
                bound_logger.debug("Closing subscription...")
                if subscription:
                    try:
                        await subscription.unsubscribe()
                        bound_logger.debug("Subscription closed")
                    except BadSubscriptionError as e:
                        bound_logger.warning(
                            "BadSubscriptionError unsubscribing from NATS: {}", e
                        )

        subscription = None
        try:
            subscription = await self._subscribe(
                group_id=group_id,
                wallet_id=wallet_id,
                topic=topic,
                state=state,
                start_time=start_time,
                state_uuid=state_uuid,
            )
            yield event_generator(subscription=subscription)
        except Exception as e:  # pylint: disable=W0718
            bound_logger.exception("Unexpected error processing events")
            raise e

    async def check_jetstream(self):
        try:
            account_info = await self.js_context.account_info()
            is_working = account_info.streams > 0
            logger.trace("JetStream check completed. Is working: {}", is_working)
            return {
                "is_working": is_working,
                "streams_count": account_info.streams,
                "consumers_count": account_info.consumers,
            }
        except Exception:  # pylint: disable=W0718
            logger.exception("Caught exception while checking jetstream status")
            return {"is_working": False}
