import asyncio
from typing import NoReturn, Optional, Set

from shared import APIRouter
from shared.log_config import get_logger
from shared.models.webhook_topics import (
    AcaPyWebhookEvent,
    CloudApiWebhookEvent,
    topic_mapping,
)
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

        self.scanned_keys = asyncio.Queue()

        self._start_background_tasks()

    def _start_background_tasks(self) -> None:
        """
        Start the background tasks as part of AcapyEventsProcessor's lifecycle
        """
        # process incoming events and cleanup queues
        asyncio.create_task(self._process_incoming_events())

    async def _process_incoming_events(self) -> NoReturn:
        while True:
            # Scan redis for keys, otherwise wait for keyspace notification event if no keys present
            # try:
            #     wallet_id = request.headers["x-wallet-id"]
            # except KeyError:
            #     ## TODO: implement different wallet_id for events from governance agent
            #     # if origin == "governance":
            #     #     wallet_id = origin
            #     # else:
            #     wallet_id = "admin"

            self._process_event(acapy_topic, wallet_id, origin, event)

    async def _scan_acapy_event_keys(self) -> Set[str]:
        collected_keys = set()
        cursor = 0  # Starting cursor value for SCAN
        logger.trace("Starting SCAN to fetch incoming ACA-Py event keys from Redis.")

        try:
            while True:  # Loop until the cursor returned by SCAN is '0'
                cursor, keys = await self.redis.scan(
                    cursor, match=f"{self.cloudapi_redis_prefix}:*", count=1000
                )
                if keys:
                    keys_batch = set(key.decode("utf-8") for key in keys)
                    collected_keys.update(keys_batch)
                    logger.trace(
                        f"Fetched {len(keys_batch)} ACA-Py event keys from Redis. Cursor value: {cursor}"
                    )
                else:
                    logger.trace("No ACA-Py event keys found in this batch.")

                if cursor == 0:  # Iteration is complete
                    logger.info(
                        f"Completed SCAN for ACA-Py event keys, fetched {len(collected_keys)} total."
                    )
                    break  # Exit the loop
        except Exception:
            logger.exception(
                "An exception occurred when fetching ACA-Py event keys from redis. Continuing..."
            )

        return collected_keys

    async def _process_event(self, acapy_topic, wallet_id, origin, event):

        bound_logger = logger.bind(
            body={
                "wallet_id": wallet_id,
                "acapy_topic": acapy_topic,
                "origin": origin,
                "body": event,
            }
        )
        bound_logger.trace("Handling received webhook event")

        # Map from the acapy webhook topic to a unified cloud api topic
        cloudapi_topic = topic_mapping.get(acapy_topic)
        if not cloudapi_topic:
            bound_logger.warning(
                "Not publishing webhook event for acapy_topic `{}` as it doesn't exist in the topic_mapping",
                acapy_topic,
            )
            return

        acapy_webhook_event = AcaPyWebhookEvent(
            payload=event,
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
                "Not publishing webhook event for topic `{}` as no transformer exists for the topic",
                cloudapi_topic,
            )
            return

        webhook_event_json = cloudapi_webhook_event.model_dump_json()

        # Add data to redis, which publishes to a redis pubsub channel that SseManager listens to
        await self.redis_service.add_cloudapi_webhook_event(
            webhook_event_json, wallet_id
        )

        bound_logger.trace("Successfully processed received webhook.")
