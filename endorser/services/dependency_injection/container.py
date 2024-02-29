import os
from typing import List

from dependency_injector import containers, providers
from redis.cluster import ClusterNode

from endorser.services.endorsement_processor import EndorsementProcessor
from shared.services.redis_service import (
    RedisService,
    init_redis_cluster_pool,
    parse_redis_nodes,
)


class Container(containers.DeclarativeContainer):
    """
    Dependency injection container for the Endorser service.

    This container is responsible for creating and managing the lifecycle of
    the Redis and EndorsementProcessor services
    """

    redis_nodes = os.getenv("REDIS_NODES", "localhost:6379")
    nodes: List[ClusterNode] = parse_redis_nodes(redis_nodes)

    # Resource provider for the Redis connection pool
    redis_cluster = providers.Resource(
        init_redis_cluster_pool,
        nodes=nodes,
        logger_name="endorser",
    )

    # Singleton provider for the WebhooksRedisService
    redis_service = providers.Singleton(
        RedisService,
        redis=redis_cluster,
        logger_name="endorser",
    )

    # Singleton provider for the ACA-Py Redis events processor
    endorsement_processor = providers.Singleton(
        EndorsementProcessor,
        redis_service=redis_service,
    )


def get_container() -> Container:
    """
    Creates a configured instance of the dependency injection container for the application.

    Returns:
        An instance of the configured Container.
    """
    return Container()
