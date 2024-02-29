import os
from contextlib import asynccontextmanager

from dependency_injector.wiring import Provide, inject
from fastapi import Depends, FastAPI, HTTPException

from endorser.services.dependency_injection.container import Container, get_container
from endorser.services.endorsement_processor import EndorsementProcessor
from shared.log_config import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def app_lifespan(_: FastAPI):
    logger.info("Endorser Service startup")

    # Initialize the container
    container = get_container()
    container.wire(modules=[__name__])

    # Start singleton services
    container.redis_service()
    endorsement_processor = container.endorsement_processor()
    endorsement_processor.start()

    yield

    logger.info("Shutdown Endorser services")
    await endorsement_processor.stop()


def create_app() -> FastAPI:
    OPENAPI_NAME = os.getenv("OPENAPI_NAME", "Aries Cloud API: Endorser Service")
    PROJECT_VERSION = os.getenv("PROJECT_VERSION", "0.11.0")

    application = FastAPI(
        title=OPENAPI_NAME,
        version=PROJECT_VERSION,
        lifespan=app_lifespan,
    )

    return application


app = create_app()


@app.get("/health")
@inject
async def health_check(
    endorsement_processor: EndorsementProcessor = Depends(
        Provide[Container.endorsement_processor]
    ),
):
    if endorsement_processor.are_tasks_running():
        return {"status": "healthy"}
    else:
        raise HTTPException(
            status_code=503, detail="One or more background tasks are not running."
        )
