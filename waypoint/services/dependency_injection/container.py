import os
from typing import List

from dependency_injector import containers, providers

from waypoint.services.nats_service import NatsEventsProcessor, init_nats_client


class Container(containers.DeclarativeContainer):
    """
    Dependency injection container for the waypoint service
    """

    jetstream = providers.Resource(init_nats_client)

    nats_events_processor = providers.Singleton(
        NatsEventsProcessor,
        jetstream=jetstream,
    )
