import asyncio
import datetime
import os
from typing import Any, Generator, List, Optional, Set

from redis.cluster import ClusterNode, RedisCluster

from shared.log_config import get_logger


class RedisConfig:
    PASSWORD = os.getenv("REDIS_PASSWORD", None)
    SSL = os.getenv("REDIS_SSL", "false").upper() == "TRUE"
    SOCKET_CONNECT_TIMEOUT = int(os.getenv("REDIS_CONNECT_TIMEOUT", "15"))
    MAX_CONNECTIONS = int(os.getenv("REDIS_MAX_CONNECTIONS", "20000"))


REDIS_CONNECTION_PARAMS = {
    "password": RedisConfig.PASSWORD,
    "ssl": RedisConfig.SSL,
    "socket_connect_timeout": RedisConfig.SOCKET_CONNECT_TIMEOUT,
    "max_connections": RedisConfig.MAX_CONNECTIONS,
}


def parse_redis_nodes(env_var_value: str) -> List[ClusterNode]:
    """
    Parses the REDIS_NODES environment variable to a list of ClusterNode.

    :param env_var_value: The value of the REDIS_NODES environment variable.
    :return: A list of ClusterNode definitions.
    """
    nodes = []
    # We assume environment variable REDIS_NODES is like "host1:port1,host2:port2"
    for node_str in (
        env_var_value.split(",") if "," in env_var_value else [env_var_value]
    ):
        host, port = node_str.split(":")
        nodes.append(ClusterNode(host=host, port=int(port)))
    return nodes


def init_redis_cluster_pool(
    nodes: List[ClusterNode], logger_name: str
) -> Generator[RedisCluster, Any, None]:
    """
    Initialize a connection pool to the Redis Cluster.

    :param nodes: List of nodes from which initial bootstrapping can be done
    """
    logger = get_logger(logger_name)
    logger.info("Initialising Redis Cluster with nodes: {}", nodes)
    cluster = RedisCluster(startup_nodes=nodes, **REDIS_CONNECTION_PARAMS)

    logger.info("Connected to Redis Cluster")
    yield cluster

    logger.info("Closing Redis connection")
    cluster.close()
    logger.info("Closed Redis connection.")


class RedisService:
    """
    A service for interacting with Redis.
    """

    def __init__(self, redis: RedisCluster, logger_name: str) -> None:
        """
        Initialize the RedisService with a Redis cluster instance.

        Args:
            redis: A Redis client instance connected to a Redis cluster server.
            logger_name: A name for the logger, useful with file logging
        """
        self.redis = redis

        self.endorsement_redis_prefix = "endorse"  # redis prefix for endorsement events

        self.logger = get_logger(logger_name)
        self.logger.info("RedisService initialised")

    def set(self, key: str, value: str) -> Optional[bool]:
        """
        Set a key and value on redis

        Args:
            key: The key to set.
            value: The value to set.

        Returns:
            A boolean indicating that the value was successfully set.
        """
        self.logger.trace("Setting key: {}, with value: {}", key, value)
        return self.redis.set(key, value=value)

    def get(self, key: str) -> Optional[str]:
        """
        Get a value from redis

        Args:
            key: The key to get.

        Returns:
            The value from redis, if the key exists
        """
        self.logger.trace("Getting key: {}", key)
        value = self.redis.get(key)
        self.logger.trace("Got value: {}", value)
        return value

    def set_lock(self, key: str, px: int = 1000) -> Optional[bool]:
        """
        Attempts to acquire a distributed lock by setting a key in Redis with an expiration time,
        if and only if the key does not already exist.

        Args:
            key: The key to set for the lock.
            px: Expiration time of the lock in milliseconds.

        Returns:
            A boolean indicating the lock was successfully acquired, or
            None if the key already exists and the lock could not be acquired.
        """
        self.logger.trace("Setting lock for key: {}; timeout: {} milliseconds", key, px)
        return self.redis.set(key, value="1", px=px, nx=True)

    def delete_key(self, key: str) -> bool:
        """
        Deletes a key from Redis.

        Parameters:
        - key: str - The key to delete.

        Returns:
        - bool: True if the key was deleted, False otherwise.
        """
        self.logger.trace("Deleting key: {}", key)
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
        self.logger.trace("Reading index {} from {}", n, key)
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
        self.logger.trace("Pop first element from list: {}", key)
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
        self.logger.trace("Starting SCAN to fetch keys matching: {}", match_pattern)

        try:
            _, keys = self.redis.scan(
                cursor=0,
                match=match_pattern,
                count=count,
                target_nodes=RedisCluster.PRIMARIES,
            )
            if keys:
                collected_keys = set(key.decode("utf-8") for key in keys)
                self.logger.debug(
                    "Scanned {} event keys from Redis", len(collected_keys)
                )
            else:
                self.logger.trace("No keys found matching pattern in this batch.")
        except Exception:  # pylint: disable=W0718
            self.logger.exception(
                "An exception occurred when scanning for keys from redis. Continuing..."
            )

        return collected_keys

    def match_keys(self, match_pattern: str = "*") -> List[bytes]:
        """
        Fetches keys from all Redis cluster nodes matching the pattern.

        Parameters:
        - match_pattern: str - The pattern to match against, e.g.: cloudapi*

        Returns:
            A set of Redis keys that match the input pattern.
        """

        return self.redis.keys(match_pattern, target_nodes=RedisCluster.PRIMARIES)

    async def _extend_lock(self, lock_key: str, interval: datetime.timedelta) -> None:
        """
        Periodically extends the lock until cancelled. To be used as an asyncio background task.

        Args:
            lock_key: The Redis key of the lock to extend.
            interval: Timedelta object representing how long to wait before extending the lock again.
        """
        retry_interval = interval.total_seconds() * 0.9
        try:
            while True:
                await asyncio.sleep(retry_interval)
                # Attempt to extend the lock by resetting its expiration time
                self.logger.debug(f"Extending expiry for lock {lock_key}")
                lock_extended = self.redis.expire(lock_key, interval)
                if not lock_extended:
                    self.logger.warning(
                        f"Failed to extend lock: {lock_key}. Lock might have been lost."
                    )
        except asyncio.CancelledError:
            self.logger.debug(f"Lock extension task for {lock_key} was cancelled.")

    def extend_lock_task(
        self, lock_key: str, interval: datetime.timedelta
    ) -> asyncio.Task:
        """
        Starts an async background task for extending a lock key.

        Args:
            lock_key: The Redis key of the lock to extend.
            interval: Timedelta object representing how long to wait before extending the lock again.
        """
        return asyncio.create_task(self._extend_lock(lock_key, interval=interval))
