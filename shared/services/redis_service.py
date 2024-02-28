import os
import time
from typing import AsyncIterator, List, Optional

from redis.cluster import ClusterNode, RedisCluster

from shared.log_config import get_logger
from shared.models.webhook_topics.base import CloudApiWebhookEventGeneric
from shared.util.rich_parsing import parse_with_error_handling

logger = get_logger(__name__)


class RedisConfig:
    MAX_CONNECTIONS = 20000
    PASSWORD = os.getenv("REDIS_PASSWORD", None)


REDIS_CONNECTION_PARAMS = {
    "max_connections": RedisConfig.MAX_CONNECTIONS,
    "password": RedisConfig.PASSWORD,
}


async def init_redis_cluster_pool(
    nodes: List[ClusterNode],
) -> AsyncIterator[RedisCluster]:
    """
    Initialize a connection pool to the Redis Cluster.

    :param nodes: List of nodes from which initial bootstrapping can be done
    """
    logger.info(f"Initialising Redis Cluster with nodes: {nodes}")
    cluster = RedisCluster(startup_nodes=nodes, **REDIS_CONNECTION_PARAMS)

    logger.info("Connected to Redis Cluster")
    yield cluster

    logger.info("Closing Redis connection")
    await cluster.close()


class RedisService:
    """
    A service for interacting with Redis to store and retrieve webhook events.
    """

    def __init__(self, redis: RedisCluster) -> None:
        """
        Initialize the RedisService with a Redis cluster instance.

        Args:
            redis: A Redis client instance connected to a Redis cluster server.
        """
        self.redis = redis

        self.sse_event_pubsub_channel = "new_sse_event"  # name of pub/sub channel

        self.acapy_redis_prefix = "acapy-record-*"  # redis prefix, ACA-Py events
        self.cloudapi_redis_prefix = "cloudapi_event"  # redis prefix, CloudAPI events

        logger.info("RedisService initialised")

    def get_cloudapi_event_redis_key(self, wallet_id: str) -> str:
        """
        Define redis prefix for CloudAPI (transformed) webhook events

        Args:
            wallet_id: The relevant wallet id
        """
        return f"{self.cloudapi_redis_prefix}:{wallet_id}"

    def lindex(self, key: str, n: int = 0) -> Optional[str]:
        """
        Fetch the element at index `n` from a list at `key`.

        Args:
            key: The Redis key of the list.
            n: The index of the element to fetch from the list.

        Returns:
            The element at the specified index in the list, or None if the index is out of range.
        """
        return self.redis.lindex(key, index=n)

    def set_lock(self, key: str, px: int = 500) -> Optional[bool]:
        """
        Attempts to acquire a distributed lock by setting a key in Redis with an expiration time,
        if and only if the key does not already exist.

        Args:
            key: The key to set for the lock.
            px: Expiration time of the lock in miliseconds.

        Returns:
            A boolean indicating the lock was successfully acquired, or
            None if the key already exists and the lock could not be acquired.
        """
        return self.redis.set(key, value="1", px=px, nx=True)

    def delete_key(self, key: str) -> bool:
        """
        Deletes a key from Redis.

        Parameters:
        - key: str - The key to delete.

        Returns:
        - bool: True if the key was deleted, False otherwise.
        """
        # Deleting the key and returning True if the command was successful
        return self.redis.delete(key) == 1

    def pop_first_list_element(self, key: str):
        """
        Pops the first element from a list in Redis.

        Parameters:
        - key: str - The Redis key of the list.

        Returns:
        - The value of the first element if the list exists and is not empty,
          None otherwise.
        """
        # Using LPOP to remove and return the first element of the list
        return self.redis.lpop(key)

    def add_cloudapi_webhook_event(self, event_json: str, wallet_id: str) -> None:
        """
        Add a CloudAPI webhook event JSON string to Redis and publish a notification.

        Args:
            event_json: The JSON string representation of the webhook event.
            wallet_id: The identifier of the wallet associated with the event.
        """
        bound_logger = logger.bind(body={"wallet_id": wallet_id, "event": event_json})
        bound_logger.trace("Write entry to redis")

        # get a nanosecond timestamp to identify this event
        timestamp_ns: int = time.time_ns()

        # Use the current timestamp as the score for the sorted set
        wallet_key = self.get_cloudapi_event_redis_key(wallet_id)
        self.redis.zadd(wallet_key, {event_json: timestamp_ns})

        broadcast_message = f"{wallet_id}:{timestamp_ns}"
        # publish that a new event has been added
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
        bound_logger = logger.bind(body={"wallet_id": wallet_id})
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
        logger.trace(
            "Fetching entries from redis by timestamp for wallet id: {}", wallet_id
        )
        wallet_key = self.get_cloudapi_event_redis_key(wallet_id)
        entries: List[bytes] = self.redis.zrangebyscore(
            wallet_key, min=start_timestamp, max=end_timestamp
        )
        entries_str: List[str] = [entry.decode() for entry in entries]
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
        logger.info("Starting SCAN to fetch all wallet IDs.")

        try:
            while True:  # Loop until the cursor returned by SCAN is '0'
                cursor, keys = self.redis.scan(
                    cursor, match=f"{self.cloudapi_redis_prefix}:*", count=1000
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

                if cursor == 0 or all(c == 0 for c in cursor.values()):
                    logger.info("Completed SCAN for wallet IDs.")
                    break  # Exit the loop
        except Exception:
            logger.exception(
                "An exception occurred when fetching wallet_ids from redis. Continuing..."
            )

        logger.info(f"Total wallet IDs fetched: {len(wallet_ids)}.")
        return list(wallet_ids)
