import os
from contextlib import asynccontextmanager

from dependency_injector.wiring import Provide, inject
from fastapi import Depends, FastAPI, HTTPException

from shared.constants import PROJECT_VERSION
from shared.log_config import get_logger
from waypoint.routes import sse
from waypoint.services.dependency_injection.container import Container
from waypoint.services.nats_service import NatsEventsProcessor

logger = get_logger(__name__)


@asynccontextmanager
async def app_lifespan(_: FastAPI):
    logger.info("Waypoint Service startup")

    container = Container()
    container.wire(modules=[__name__, sse])

    events_processor = container.nats_events_processor()

    yield

    logger.info("Shutting down Waypoint services...")
    await events_processor.stop()
    logger.info("Waypoint Service shutdown")


def create_app() -> FastAPI:
    openapi_name = os.getenv("OPENAPI_NAME", "Waypoint Service")

    application = FastAPI(
        title=openapi_name,
        description="""
        Welcome to the OpenAPI interface for the Waypoint Service.
        The Waypoint Service enables the ability to wait for a specific event to occur before continuing.
        """,
        version=PROJECT_VERSION,
        lifespan=app_lifespan,
    )

    application.include_router(sse.router)

    return application


logger.info("Waypoint Service startup")

app = create_app()

# TODO add a health check endpoint
