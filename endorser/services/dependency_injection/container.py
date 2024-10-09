import os
from typing import List

from dependency_injector import containers, providers
from redis.cluster import ClusterNode

from endorser.services.endorsement_processor import EndorsementProcessor
from shared.services.nats_jetstream import init_nats_client


class Container(containers.DeclarativeContainer):
    """
    Dependency injection container for the Endorser service.

    This container is responsible for creating and managing the lifecycle of
    the Redis and EndorsementProcessor services
    """

    jetstream = providers.Resource(init_nats_client)

    # Singleton provider for the ACA-Py Redis events processor
    endorsement_processor = providers.Singleton(
        EndorsementProcessor,
        jetstream=jetstream,
    )
