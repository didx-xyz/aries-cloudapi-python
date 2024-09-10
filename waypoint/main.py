import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from shared.constants import PROJECT_VERSION
from shared.log_config import get_logger
from waypoint.routes import sse
from waypoint.services.dependency_injection.container import Container

logger = get_logger(__name__)


@asynccontextmanager
async def app_lifespan(_: FastAPI):
    logger.info("Waypoint Service startup")

    container = Container()
    await container.init_resources()

    container.wire(modules=[__name__, sse])

    events_processor = await container.nats_events_processor()

    yield

    logger.debug("Shutting down Waypoint service...")
    await events_processor.stop()
    await container.shutdown_resources()
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

# TODO - Improve health checks
@app.get("/health/live")
async def health_live():
    return {"status": "live"}

@app.get("/health/ready")
async def health_ready():
    return {"status": "ready"}
