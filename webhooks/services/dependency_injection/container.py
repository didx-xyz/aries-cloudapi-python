from typing import List

from dependency_injector import containers, providers
from redis.cluster import ClusterNode

from webhooks.services.redis_service import RedisService, init_redis_cluster_pool
from webhooks.services.sse_manager import SseManager


def parse_redis_nodes(env_var_value: str) -> List[ClusterNode]:
    """
    Parses the REDIS_NODES environment variable to a list of ClusterNode.

    :param env_var_value: The value of the REDIS_NODES environment variable.
    :return: A list of ClusterNode definitions.
    """
    nodes = []
    # We assume environment variable REDIS_NODES is like "host1:port1,host2:port2"
    for node_str in env_var_value.split(","):
        host, port = node_str.split(":")
        nodes.append(ClusterNode(host=host, port=int(port)))
    return nodes


class Container(containers.DeclarativeContainer):
    """
    Dependency injection container for the webhooks service.

    This container is responsible for creating and managing the lifecycle of
    the Redis and SseManager services, used throughout the webhooks application.
    It defines the configuration and instantiation of the services.
    """

    # Configuration provider for environment variables and other settings
    config = providers.Configuration()

    nodes: List[ClusterNode] = parse_redis_nodes(config.nodes)

    # Resource provider for the Redis connection pool
    redis_cluster = providers.Resource(
        init_redis_cluster_pool,
        nodes=nodes,
    )

    # Singleton provider for the RedisService
    redis_service = providers.Singleton(
        RedisService,
        redis=redis_cluster,
    )

    # Singleton provider for the SseManager
    sse_manager = providers.Singleton(
        SseManager,
        redis_service=redis_service,
    )


def get_container() -> Container:
    """
    Creates and configures the dependency injection container for the application.

    This function configures the Redis nodes. It prepares the container to be wired
    into the application modules, enabling dependency injection throughout the app.

    Returns:
        An instance of the configured Container.
    """
    configured_container = Container()

    configured_container.config.redis_nodes.from_env("REDIS_NODES", "localhost:6379")

    return configured_container
