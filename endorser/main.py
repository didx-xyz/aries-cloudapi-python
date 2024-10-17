import os
import asyncio
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
    await container.shutdown_resources()
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


@app.get("/health/live")
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


@app.get("/health/ready")
@inject
async def health_ready(
    endorsement_processor: EndorsementProcessor = Depends(
        Provide[Container.endorsement_processor]
    ),
):
    try:
        jetstream_status = await asyncio.wait_for(
            endorsement_processor.check_jetstream(), timeout=5.0
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=503,
            detail={"status": "not ready", "error": "JetStream health check timed out"},
        )
    except Exception as e:  # pylint: disable=W0718
        raise HTTPException(
            status_code=500, detail={"status": "error", "error": str(e)}
        )

    if jetstream_status["is_working"]:
        return {"status": "ready", "jetstream": jetstream_status}
    else:
        raise HTTPException(
            status_code=503,
            detail={"status": "not ready", "jetstream": "JetStream not ready"},
        )
