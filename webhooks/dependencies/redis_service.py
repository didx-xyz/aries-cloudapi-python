import time
from typing import AsyncIterator, List

import aioredis
from aioredis import Redis

from shared.log_config import get_logger
from shared.models.webhook_topics.base import CloudApiWebhookEvent
from shared.util.rich_parsing import parse_with_error_handling

logger = get_logger(__name__)


async def init_redis_pool(host: str, password: str) -> AsyncIterator[Redis]:
    pool = await aioredis.from_url(f"redis://{host}", password=password)
    yield pool
    pool.close()
    await pool.wait_closed()


class RedisService:
    """
    A service for interacting with Redis to store and retrieve webhook events.
    """

    def __init__(self, redis: Redis) -> None:
        """
        Initialize the RedisService with a Redis client instance.

        Args:
            redis: A Redis client instance connected to a Redis server.
        """
        self.redis = redis

        self.sse_event_pubsub_channel = "new_sse_event"  # name of pub/sub channel
        self.wallet_id_key = "wallet_id"  # name of pub/sub channel

    async def add_webhook_event(self, wallet_id: str, event_json: str) -> None:
        """
        Add a webhook event JSON string to Redis and publish a notification.

        Args:
            wallet_id: The identifier of the wallet associated with the event.
            event_json: The JSON string representation of the webhook event.
        """
        bound_logger = logger.bind(body={"wallet_id": wallet_id, "event": event_json})
        bound_logger.trace("Write entry to redis")

        # get a nanosecond timestamp to identify this event
        timestamp_ns: int = time.time_ns()

        # Use the current timestamp as the score for the sorted set
        wallet_key = f"{self.wallet_id_key}:{wallet_id}"
        await self.redis.zadd(wallet_key, {event_json: timestamp_ns})

        broadcast_message = f"{wallet_id}:{timestamp_ns}"
        # publish that a new event has been added
        await self.redis.publish(self.sse_event_pubsub_channel, broadcast_message)

        bound_logger.trace("Successfully wrote entry to redis.")

    async def get_json_webhook_events_by_wallet(self, wallet_id: str) -> List[str]:
        """
        Retrieve all webhook event JSON strings for a specified wallet ID.

        Args:
            wallet_id: The identifier of the wallet for which events are retrieved.

        Returns:
            A list of event JSON strings.
        """
        bound_logger = logger.bind(body={"wallet_id": wallet_id})
        bound_logger.trace("Fetching entries from redis by wallet id")

        # Fetch all entries using the full range of scores
        wallet_key = f"{self.wallet_id_key}:{wallet_id}"
        entries: List[bytes] = await self.redis.zrange(wallet_key, 0, -1)
        entries_str: List[str] = [entry.decode() for entry in entries]

        bound_logger.trace("Successfully fetched redis entries.")
        return entries_str

    async def get_webhook_events_by_wallet(
        self, wallet_id: str
    ) -> List[CloudApiWebhookEvent]:
        """
        Retrieve all webhook events for a specified wallet ID, parsed as CloudApiWebhookEvent objects.

        Args:
            wallet_id: The identifier of the wallet for which events are retrieved.

        Returns:
            A list of CloudApiWebhookEvent instances.
        """
        entries = await self.get_json_webhook_events_by_wallet(wallet_id)
        parsed_entries = [
            parse_with_error_handling(CloudApiWebhookEvent, entry) for entry in entries
        ]
        return parsed_entries

    async def get_json_webhook_events_by_wallet_and_topic(
        self, wallet_id: str, topic: str
    ) -> List[str]:
        """
        Retrieve all webhook event JSON strings for a specified wallet ID and topic.

        Args:
            wallet_id: The identifier of the wallet for which events are retrieved.
            topic: The topic to filter the events by.

        Returns:
            A list of event JSON strings that match the specified topic.
        """
        entries = await self.get_json_webhook_events_by_wallet(wallet_id)
        # Filter the json entry for our requested topic without deserialising
        topic_str = f'"topic":"{topic}"'
        return [entry for entry in entries if topic_str in entry]

    async def get_webhook_events_by_wallet_and_topic(
        self, wallet_id: str, topic: str
    ) -> List[CloudApiWebhookEvent]:
        """
        Retrieve all webhook events for a specified wallet ID and topic, parsed as CloudApiWebhookEvent objects.

        Args:
            wallet_id: The identifier of the wallet for which events are retrieved.
            topic: The topic to filter the events by.

        Returns:
            A list of CloudApiWebhookEvent instances that match the specified topic.
        """
        entries = await self.get_webhook_events_by_wallet(wallet_id)
        return [entry for entry in entries if topic == entry.topic]

    async def get_json_events_by_timestamp(
        self, wallet_id: str, start_timestamp: float, end_timestamp: float = "+inf"
    ) -> List[str]:
        """
        Retrieve all webhook event JSON strings for a specified wallet ID within a timestamp range.

        Args:
            wallet_id: The identifier of the wallet for which events are retrieved.
            start_timestamp: The start of the timestamp range.
            end_timestamp: The end of the timestamp range (defaults to "+inf" for no upper limit).

        Returns:
            A list of event JSON strings that fall within the specified timestamp range.
        """
        logger.trace(
            "Fetching entries from redis by timestamp for wallet id: {}", wallet_id
        )
        wallet_key = f"{self.wallet_id_key}:{wallet_id}"
        entries = await self.redis.zrangebyscore(
            wallet_key, min=start_timestamp, max=end_timestamp
        )
        return entries

    async def get_events_by_timestamp(
        self, wallet_id: str, start_timestamp: float, end_timestamp: float = "+inf"
    ) -> List[CloudApiWebhookEvent]:
        """
        Retrieve all webhook events for a specified wallet ID within a timestamp range, parsed as CloudApiWebhookEvent
         objects.

        Args:
            wallet_id: The identifier of the wallet for which events are retrieved.
            start_timestamp: The start of the timestamp range.
            end_timestamp: The end of the timestamp range (defaults to "+inf" for no upper limit).

        Returns:
            A list of CloudApiWebhookEvent instances that fall within the specified timestamp range.
        """
        entries = await self.get_json_events_by_timestamp(
            wallet_id, start_timestamp, end_timestamp
        )
        parsed_entries = [
            parse_with_error_handling(CloudApiWebhookEvent, entry) for entry in entries
        ]
        return parsed_entries

    async def get_all_wallet_ids(self) -> List[str]:
        """
        Fetch all wallet IDs that have events stored in Redis.
        """
        wallet_ids = set()
        cursor = 0  # Starting cursor value for SCAN
        logger.info("Starting SCAN to fetch all wallet IDs.")

        try:
            while True:  # Loop until the cursor returned by SCAN is '0'
                cursor, keys = await self.redis.scan(
                    cursor, match="wallet_id:*", count=1000
                )
                if keys:
                    wallet_id_batch = set(
                        key.decode("utf-8").split(":")[1] for key in keys
                    )
                    wallet_ids.update(wallet_id_batch)
                    logger.debug(
                        f"Fetched {len(wallet_id_batch)} wallet IDs from Redis. Cursor value: {cursor}"
                    )
                else:
                    logger.debug("No wallet IDs found in this batch.")

                if cursor == 0:  # Iteration is complete
                    logger.info("Completed SCAN for wallet IDs.")
                    break  # Exit the loop
        except Exception:
            logger.exception(
                "An exception occurred when fetching wallet_ids from redis. Continuing..."
            )

        logger.info(f"Total wallet IDs fetched: {len(wallet_ids)}.")
        return list(wallet_ids)
