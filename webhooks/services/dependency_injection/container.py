import os
from typing import List

from dependency_injector import containers, providers
from redis.cluster import ClusterNode

from shared.services.redis_service import init_redis_cluster_pool, parse_redis_nodes
from webhooks.services.acapy_events_processor import AcaPyEventsProcessor
from webhooks.services.billing_processor import BillingManager
from webhooks.services.sse_manager import SseManager
from webhooks.services.webhooks_redis_service import WebhooksRedisService


class Container(containers.DeclarativeContainer):
    """
    Dependency injection container for the webhooks service.

    This container is responsible for creating and managing the lifecycle of
    the Redis and SseManager services, used throughout the webhooks application.
    It defines the configuration and instantiation of the services.
    """

    # Configuration provider for environment variables and other settings
    config = providers.Configuration()

    redis_nodes = os.getenv("REDIS_NODES", "localhost:6379")
    nodes: List[ClusterNode] = parse_redis_nodes(redis_nodes)

    # Resource provider for the Redis connection pool
    redis_cluster = providers.Resource(
        init_redis_cluster_pool,
        nodes=nodes,
        logger_name="webhooks.redis",
    )

    # Singleton provider for the WebhooksRedisService
    redis_service = providers.Singleton(
        WebhooksRedisService,
        redis=redis_cluster,
    )

    # Singleton provider for the ACA-Py Redis events processor
    acapy_events_processor = providers.Singleton(
        AcaPyEventsProcessor,
        redis_service=redis_service,
    )

    # Singleton provider for the SseManager
    sse_manager = providers.Singleton(
        SseManager,
        redis_service=redis_service,
    )

    # Singleton provider for the BillingManager
    billing_manager = providers.Singleton(
        BillingManager,
        redis_service=redis_service,
    )


def get_container() -> Container:
    """
    Creates a configured instance of the dependency injection container for the application.

    Returns:
        An instance of the configured Container.
    """
    return Container()
