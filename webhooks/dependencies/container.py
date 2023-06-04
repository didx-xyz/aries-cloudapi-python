from dependency_injector import containers, providers

from webhooks.dependencies import redis, service


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    redis_pool = providers.Resource(
        redis.init_redis_pool,
        host=config.redis_host,
        password=config.redis_password,
    )
    service = providers.Factory(
        service.Service,
        redis=redis_pool,
    )


def get_container():
    configured_container = Container()
    configured_container.config.redis_host.from_env("REDIS_HOST", "wh-redis")
    configured_container.config.redis_password.from_env("REDIS_PASSWORD", "")
    return configured_container
