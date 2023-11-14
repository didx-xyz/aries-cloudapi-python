from dependency_injector import containers, providers

from webhooks.dependencies.redis_service import RedisService, init_redis_pool
from webhooks.dependencies.sse_manager import SseManager


class Container(containers.DeclarativeContainer):
    """
    Dependency injection container for the webhooks service.

    This container is responsible for creating and managing the lifecycle of
    the Redis and SseManager services, used throughout the webhooks application.
    It defines the configuration and instantiation of the services.
    """

    # Configuration provider for environment variables and other settings
    config = providers.Configuration()

    # Resource provider for the Redis connection pool
    redis_pool = providers.Resource(
        init_redis_pool,
        host=config.redis_host,
        password=config.redis_password,
    )

    # Singleton provider for the RedisService
    redis_service = providers.Singleton(
        RedisService,
        redis=redis_pool,
    )

    # Singleton provider for the SseManager
    sse_manager = providers.Singleton(
        SseManager,
        redis_service=redis_service,
    )


def get_container() -> Container:
    """
    Creates and configures the dependency injection container for the application.

    This function configures the Redis host and password. It prepares the container
    to be wired into the application modules, enabling dependency injection throughout the app.

    Returns:
        An instance of the configured Container.
    """
    configured_container = Container()
    # Load configuration from environment variables with defaults
    configured_container.config.redis_host.from_env("REDIS_HOST", "localhost")
    configured_container.config.redis_password.from_env("REDIS_PASSWORD", "")
    return configured_container
