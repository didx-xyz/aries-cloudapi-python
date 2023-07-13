import io
import os
import traceback
from distutils.util import strtobool

import pydantic
import yaml
from aiohttp import ClientResponseError
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse

from app.admin.tenants import tenants
from shared.log_config import get_logger
from app.event_handling.webhooks import Webhooks
from app.exceptions.cloud_api_error import CloudApiException
from app.generic import definitions, messaging, sse, trust_registry, webhooks
from app.generic.connections import connections
from app.generic.issuer import issuer
from app.generic.jsonld import jsonld
from app.generic.oob import oob
from app.generic.verifier import verifier
from app.generic.wallet import wallet

OPENAPI_NAME = os.getenv("OPENAPI_NAME", "OpenAPI")
PROJECT_VERSION = os.getenv("PROJECT_VERSION", "0.8.1-beta1")

logger = get_logger(__name__)
prod = strtobool(os.environ.get("prod", "True"))
debug = not prod


def create_app() -> FastAPI:
    routes = [
        connections,
        definitions,
        issuer,
        jsonld,
        messaging,
        oob,
        tenants,
        trust_registry,
        verifier,
        wallet,
        webhooks,
        sse,
    ]

    application = FastAPI(
        debug=debug,
        title=OPENAPI_NAME,
        description="Welcome to the Aries CloudAPI Python project",
        version=PROJECT_VERSION,
    )

    for route in routes:
        # Routes will appear in the openapi docs with the same order as defined in `routes`
        application.include_router(route.router)

    return application


app = create_app()


@app.on_event("startup")
async def startup_event():
    logger.info("Calling Webhooks startup")
    await Webhooks.start_webhook_client()


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Calling Webhooks shutdown")
    await Webhooks.shutdown()


# add endpoints
# additional yaml version of openapi.json
@app.get("/openapi.yaml", include_in_schema=False)
def read_openapi_yaml() -> Response:
    logger.info("GET request received: OpenAPI yaml endpoint")
    openapi_json = app.openapi()
    yaml_s = io.StringIO()
    yaml.dump(openapi_json, yaml_s, allow_unicode=True, sort_keys=False)
    logger.info("Returning OpenAPI yaml text.")
    return Response(content=yaml_s.getvalue(), media_type="text/yaml")


@app.exception_handler(Exception)
async def client_response_error_exception_handler(
    request: Request, exception: Exception
):
    stacktrace = {"stack": traceback.format_exc()}

    if isinstance(exception, ClientResponseError):
        return JSONResponse(
            {"detail": exception.message, **(stacktrace if debug else {})},
            exception.status or 500,
        )
    if isinstance(exception, CloudApiException):
        return JSONResponse(
            {"detail": exception.detail, **(stacktrace if debug else {})},
            exception.status_code,
        )
    if isinstance(exception, HTTPException):
        return JSONResponse(
            {**exception.detail, **(stacktrace if debug else {})},
            exception.status_code,
            exception.headers,
        )
    if isinstance(exception, pydantic.error_wrappers.ValidationError):
        return JSONResponse({"detail": exception.errors()}, status_code=422)
    else:
        return JSONResponse(
            {"detail": "Internal server error", "exception": str(exception)}, 500
        )
