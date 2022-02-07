import io
import logging
import os
from distutils.util import strtobool
import sys

import pydantic
import yaml
from aiohttp import ClientResponseError
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from fastapi_websocket_pubsub import PubSubClient

from app.admin.governance import credential_definitions, schemas
from app.admin.governance.multitenant_wallet import wallet_admin
from app.generic import messaging, trust_registry, webhooks
from app.generic.connections import connections
from app.generic.issuer import issuer
from app.generic.verifier import verifier
from app.generic.wallet import wallet

logger = logging.getLogger(__name__)
prod = strtobool(os.environ.get("prod", "True"))
app = FastAPI(debug=not prod)

app.include_router(connections.router)
app.include_router(issuer.router)
app.include_router(messaging.router)
app.include_router(wallet.router)
app.include_router(wallet_admin.router)
app.include_router(verifier.router)
app.include_router(schemas.router)
app.include_router(credential_definitions.router)
app.include_router(trust_registry.router)
app.include_router(webhooks.router)

sys.path.append(os.path.abspath(os.path.join(os.path.basename(__file__), "..")))

PORT = os.getenv("PORT", "3010")
URL = os.getenv("BROADCAST_URL", "yoma-webhooks-web")


# Callback to be called upon event being published on server
async def on_event(topic, data):
    print("Trigger URL was accessed")
    print(f"{topic}: {data}")


import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.basename(__file__), "..")))


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
    if isinstance(exception, ClientResponseError):
        return JSONResponse({"detail": exception.message}, exception.status or 500)
    if isinstance(exception, HTTPException):
        return JSONResponse(exception.detail, exception.status_code, exception.headers)
    if isinstance(exception, pydantic.error_wrappers.ValidationError):
        return JSONResponse({"detail": exception.errors()}, status_code=422)
    else:
        return JSONResponse({"detail": "Internal server error"}, 500)
