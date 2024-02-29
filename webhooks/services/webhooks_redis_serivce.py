from typing import List
from uuid import uuid4

from redis import RedisCluster

from shared.models.webhook_topics.base import CloudApiWebhookEventGeneric
from shared.services.redis_service import RedisService
from shared.util.rich_parsing import parse_with_error_handling


class WebhooksRedisService(RedisService):
    """
    A service for interacting with Redis to store and retrieve webhook events.
    """

    def __init__(self, redis: RedisCluster) -> None:
        """
        Initialize the WebhooksRedisService with a Redis cluster instance.

        Args:
            redis: A Redis client instance connected to a Redis cluster server.
        """
        super().__init__(redis=redis, logger_name="webhooks")

        self.sse_event_pubsub_channel = "new_sse_event"  # name of pub/sub channel

        self.acapy_redis_prefix = "acapy-record-*"  # redis prefix, ACA-Py events

        self.logger.info("WebhooksRedisService initialised")

    def add_endorsement_event(self, event_json: str, transaction_id: str) -> None:
        """
        Add an endorsement event to bespoke prefix for the endorsement service.

        Args:
            event_json: The JSON string representation of the endorsement event.
            transaction_id: The transaction id associated with the event.
        """
        self.logger.trace("Write endorsement entry to redis")

        # Define key for this transaction_id, appending uuid4 to ensure uniqueness
        redis_key = f"{self.endorsement_redis_prefix}:{transaction_id}:{uuid4().hex}"
        self.set(key=redis_key, value=event_json)

        self.logger.trace("Successfully wrote endorsement entry to redis.")

    def add_cloudapi_webhook_event(
        self, event_json: str, wallet_id: str, timestamp_ns: int
    ) -> None:
        """
        Add a CloudAPI webhook event JSON string to Redis and publish a notification.

        Args:
            event_json: The JSON string representation of the webhook event.
            wallet_id: The identifier of the wallet associated with the event.
            timestamp_ns: The timestamp (in nanoseconds) of when the event was saved.
        """
        bound_logger = self.logger.bind(
            body={"wallet_id": wallet_id, "event": event_json}
        )
        bound_logger.trace("Write entry to redis")

        # Use the current timestamp as the score for the sorted set
        wallet_key = self.get_cloudapi_event_redis_key(wallet_id)
        self.redis.zadd(wallet_key, {event_json: timestamp_ns})

        broadcast_message = f"{wallet_id}:{timestamp_ns}"
        # publish that a new event has been added
        bound_logger.trace(f"Publishing message on pubsub channel: {broadcast_message}")
        self.redis.publish(self.sse_event_pubsub_channel, broadcast_message)

        bound_logger.trace("Successfully wrote entry to redis.")

    def get_json_cloudapi_events_by_wallet(self, wallet_id: str) -> List[str]:
        """
        Retrieve all CloudAPI webhook event JSON strings for a specified wallet ID.

        Args:
            wallet_id: The identifier of the wallet for which events are retrieved.

        Returns:
            A list of event JSON strings.
        """
        bound_logger = self.logger.bind(body={"wallet_id": wallet_id})
        bound_logger.trace("Fetching entries from redis by wallet id")

        # Fetch all entries using the full range of scores
        wallet_key = self.get_cloudapi_event_redis_key(wallet_id)
        entries: List[bytes] = self.redis.zrange(wallet_key, 0, -1)
        entries_str: List[str] = [entry.decode() for entry in entries]

        bound_logger.trace("Successfully fetched redis entries.")
        return entries_str

    def get_cloudapi_events_by_wallet(
        self, wallet_id: str
    ) -> List[CloudApiWebhookEventGeneric]:
        """
        Retrieve all CloudAPI webhook events for a specified wallet ID,
        parsed as CloudApiWebhookEventGeneric objects.

        Args:
            wallet_id: The identifier of the wallet for which events are retrieved.

        Returns:
            A list of CloudApiWebhookEventGeneric instances.
        """
        entries = self.get_json_cloudapi_events_by_wallet(wallet_id)
        parsed_entries = [
            parse_with_error_handling(CloudApiWebhookEventGeneric, entry)
            for entry in entries
        ]
        return parsed_entries

    def get_json_cloudapi_events_by_wallet_and_topic(
        self, wallet_id: str, topic: str
    ) -> List[str]:
        """
        Retrieve all CloudAPI webhook event JSON strings for a specified wallet ID and topic.

        Args:
            wallet_id: The identifier of the wallet for which events are retrieved.
            topic: The topic to filter the events by.

        Returns:
            A list of event JSON strings that match the specified topic.
        """
        entries = self.get_json_cloudapi_events_by_wallet(wallet_id)
        # Filter the json entry for our requested topic without deserialising
        topic_str = f'"topic":"{topic}"'
        return [entry for entry in entries if topic_str in entry]

    def get_cloudapi_events_by_wallet_and_topic(
        self, wallet_id: str, topic: str
    ) -> List[CloudApiWebhookEventGeneric]:
        """
        Retrieve all CloudAPI webhook events for a specified wallet ID and topic,
        parsed as CloudApiWebhookEventGeneric objects.

        Args:
            wallet_id: The identifier of the wallet for which events are retrieved.
            topic: The topic to filter the events by.

        Returns:
            A list of CloudApiWebhookEventGeneric instances that match the specified topic.
        """
        entries = self.get_cloudapi_events_by_wallet(wallet_id)
        return [entry for entry in entries if topic == entry.topic]

    def get_json_cloudapi_events_by_timestamp(
        self, wallet_id: str, start_timestamp: float, end_timestamp: float = "+inf"
    ) -> List[str]:
        """
        Retrieve all CloudAPI webhook event JSON strings for a specified wallet ID within a timestamp range.

        Args:
            wallet_id: The identifier of the wallet for which events are retrieved.
            start_timestamp: The start of the timestamp range.
            end_timestamp: The end of the timestamp range (defaults to "+inf" for no upper limit).

        Returns:
            A list of event JSON strings that fall within the specified timestamp range.
        """
        bound_logger = self.logger.bind(body={"wallet_id": wallet_id})
        bound_logger.debug("Fetching entries from redis by timestamp for wallet")
        wallet_key = self.get_cloudapi_event_redis_key(wallet_id)
        entries: List[bytes] = self.redis.zrangebyscore(
            wallet_key, min=start_timestamp, max=end_timestamp
        )
        entries_str: List[str] = [entry.decode() for entry in entries]
        bound_logger.trace("Fetched entries: {}", entries_str)
        return entries_str

    def get_cloudapi_events_by_timestamp(
        self, wallet_id: str, start_timestamp: float, end_timestamp: float = "+inf"
    ) -> List[CloudApiWebhookEventGeneric]:
        """
        Retrieve all CloudAPI webhook events for a specified wallet ID within a timestamp range,
        parsed as CloudApiWebhookEventGeneric objects.

        Args:
            wallet_id: The identifier of the wallet for which events are retrieved.
            start_timestamp: The start of the timestamp range.
            end_timestamp: The end of the timestamp range (defaults to "+inf" for no upper limit).

        Returns:
            A list of CloudApiWebhookEventGeneric instances that fall within the specified timestamp range.
        """
        entries = self.get_json_cloudapi_events_by_timestamp(
            wallet_id, start_timestamp, end_timestamp
        )
        parsed_entries = [
            parse_with_error_handling(CloudApiWebhookEventGeneric, entry)
            for entry in entries
        ]
        return parsed_entries

    def get_all_cloudapi_wallet_ids(self) -> List[str]:
        """
        Fetch all wallet IDs that have CloudAPI webhook events stored in Redis.
        """
        wallet_ids = set()
        cursor = 0  # Starting cursor value for SCAN
        self.logger.info("Starting SCAN to fetch all wallet IDs.")

        try:
            while True:  # Loop until the cursor returned by SCAN is '0'
                next_cursor, keys = self.redis.scan(
                    cursor, match=f"{self.cloudapi_redis_prefix}:*", count=10000
                )
                if keys:
                    wallet_id_batch = set(
                        key.decode("utf-8").split(":")[1] for key in keys
                    )
                    wallet_ids.update(wallet_id_batch)
                    self.logger.debug(
                        f"Fetched {len(wallet_id_batch)} wallet IDs from Redis. Cursor value: {cursor}"
                    )
                else:
                    self.logger.debug("No wallet IDs found in this batch.")

                if all(c == 0 for c in next_cursor.values()):
                    self.logger.info("Completed SCAN for wallet IDs.")
                    break  # Exit the loop
                cursor += 1
        except Exception:
            self.logger.exception(
                "An exception occurred when fetching wallet_ids from redis. Continuing..."
            )

        self.logger.info(f"Total wallet IDs fetched: {len(wallet_ids)}.")
        return list(wallet_ids)
