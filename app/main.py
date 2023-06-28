import io
import logging
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
from app.event_handling.websocket_manager import WebsocketManager
from app.exceptions.cloud_api_error import CloudApiException
from app.generic import definitions, messaging, trust_registry
from app.generic.connections import connections
from app.generic.issuer import issuer
from app.generic.jsonld import jsonld
from app.generic.oob import oob
from app.generic.verifier import verifier
from app.generic.wallet import wallet
from app.generic.webhooks import sse, webhooks, websocket_endpoint

logger = logging.getLogger(__name__)

prod = strtobool(os.environ.get("prod", "True"))
debug = not prod

OPENAPI_NAME = os.getenv("OPENAPI_NAME", "OpenAPI")
PROJECT_VERSION = os.getenv("PROJECT_VERSION", "0.8.0-beta1")


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
        websocket_endpoint,
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
    await WebsocketManager.start_pubsub_client()


@app.on_event("shutdown")
async def shutdown_event():
    await WebsocketManager.shutdown()


# add endpoints
# additional yaml version of openapi.json
@app.get("/openapi.yaml", include_in_schema=False)
def read_openapi_yaml() -> Response:
    openapi_json = app.openapi()
    yaml_s = io.StringIO()
    yaml.dump(openapi_json, yaml_s, allow_unicode=True, sort_keys=False)
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
