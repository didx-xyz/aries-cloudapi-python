import os
from typing import AsyncIterator, List, Optional, Set

from redis.cluster import ClusterNode, RedisCluster

from shared.log_config import get_logger


class RedisConfig:
    MAX_CONNECTIONS = 20000
    PASSWORD = os.getenv("REDIS_PASSWORD", None)


REDIS_CONNECTION_PARAMS = {
    "max_connections": RedisConfig.MAX_CONNECTIONS,
    "password": RedisConfig.PASSWORD,
}


async def init_redis_cluster_pool(
    nodes: List[ClusterNode], logger_name: str
) -> AsyncIterator[RedisCluster]:
    """
    Initialize a connection pool to the Redis Cluster.

    :param nodes: List of nodes from which initial bootstrapping can be done
    """
    logger = get_logger(logger_name)
    logger.info(f"Initialising Redis Cluster with nodes: {nodes}")
    cluster = RedisCluster(startup_nodes=nodes, **REDIS_CONNECTION_PARAMS)

    logger.info("Connected to Redis Cluster")
    yield cluster

    logger.info("Closing Redis connection")
    await cluster.close()


class RedisService:
    """
    A service for interacting with Redis.
    """

    def __init__(self, redis: RedisCluster, logger_name: str = "redis") -> None:
        """
        Initialize the RedisService with a Redis cluster instance.

        Args:
            redis: A Redis client instance connected to a Redis cluster server.
        """
        self.redis = redis

        self.cloudapi_redis_prefix = "cloudapi_event"  # redis prefix, CloudAPI events

        self.logger = get_logger(logger_name)
        self.logger.info("RedisService initialised")

    def get_cloudapi_event_redis_key(self, wallet_id: str) -> str:
        """
        Define redis prefix for CloudAPI (transformed) webhook events

        Args:
            wallet_id: The relevant wallet id
        """
        return f"{self.cloudapi_redis_prefix}:{wallet_id}"

    def set(self, key: str, value: str) -> Optional[bool]:
        """
        Set a key and value on redis

        Args:
            key: The key to set.
            value: The value to set.

        Returns:
            A boolean indicating that the value was successfully set.
        """
        self.logger.trace(f"Setting key: {key}, with value: {value}")
        return self.redis.set(key, value=value)

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
        self.logger.trace(f"Setting lock for key: {key}; timeout: {px} milliseconds")
        return self.redis.set(key, value="1", px=px, nx=True)

    def delete_key(self, key: str) -> bool:
        """
        Deletes a key from Redis.

        Parameters:
        - key: str - The key to delete.

        Returns:
        - bool: True if the key was deleted, False otherwise.
        """
        self.logger.trace(f"Deleting key: {key}")
        # Deleting the key and returning True if the command was successful
        return self.redis.delete(key) == 1

    def lindex(self, key: str, n: int = 0) -> Optional[str]:
        """
        Fetch the element at index `n` from a list at `key`.

        Args:
            key: The Redis key of the list.
            n: The index of the element to fetch from the list.

        Returns:
            The element at the specified index in the list, or None if the index is out of range.
        """
        self.logger.trace(f"Reading {n} index from {key}")
        return self.redis.lindex(key, index=n)

    def pop_first_list_element(self, key: str):
        """
        Pops the first element from a list in Redis.

        Parameters:
        - key: str - The Redis key of the list.

        Returns:
        - The value of the first element if the list exists and is not empty,
          None otherwise.
        """
        self.logger.trace(f"Pop first element from list: {key}")
        # Using LPOP to remove and return the first element of the list
        return self.redis.lpop(key)

    def scan_keys(self, match_pattern: str, count: int) -> Set[str]:
        """
        Scans Redis for keys matching the pattern. Performs one scan for max `count` keys.

        Parameters:
        - match_pattern: str - The pattern to match against, e.g.: acapy-record-*
        - count: int - The max number of keys to return in the scan

        Returns:
            A set of Redis keys that match the input pattern.
        """
        collected_keys = set()
        self.logger.trace(f"Starting SCAN to fetch keys matching: {match_pattern}")

        try:
            _, keys = self.redis.scan(cursor=0, match=match_pattern, count=count)
            if keys:
                collected_keys = set(key.decode("utf-8") for key in keys)
                self.logger.debug(
                    f"Scanned {len(collected_keys)} event keys from Redis"
                )
            else:
                self.logger.trace("No keys found matching pattern in this batch.")
        except Exception:
            self.logger.exception(
                "An exception occurred when scanning for keys from redis. Continuing..."
            )

        return collected_keys
