import os
from contextlib import asynccontextmanager

from dependency_injector.wiring import Provide, inject
from fastapi import Depends, FastAPI, HTTPException
from scalar_fastapi import get_scalar_api_reference

from endorser.services.dependency_injection.container import Container
from endorser.services.endorsement_processor import EndorsementProcessor
from shared.constants import PROJECT_VERSION
from shared.log_config import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def app_lifespan(_: FastAPI):
    logger.info("Endorser Service startup")

    # Initialize the container
    container = Container()
    await container.init_resources()
    container.wire(modules=[__name__])

    endorsement_processor = await container.endorsement_processor()
    endorsement_processor.start()
    yield

    logger.info("Shutting down Endorser services ...")
    await endorsement_processor.stop()
    await container.shutdown_resources()  # shutdown redis instance
    logger.info("Shutdown Endorser services.")


def create_app() -> FastAPI:
    openapi_name = os.getenv("OPENAPI_NAME", "Aries Cloud API: Endorser Service")

    application = FastAPI(
        title=openapi_name,
        version=PROJECT_VERSION,
        lifespan=app_lifespan,
        redoc_url=None,
        docs_url=None,
    )

    return application


app = create_app()


# Use Scalar instead of Swagger
@app.get("/docs", include_in_schema=False)
async def scalar_html():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=app.title,
    )


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
