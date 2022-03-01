import io
import logging
import os
from distutils.util import strtobool

import yaml
from aiohttp import ClientResponseError
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from app.admin.governance import credential_definitions, schemas
from app.admin.governance.multitenant_wallet import wallet_admin
from app.generic import messaging, trust_registry
from app.generic.connections import connections
from app.generic.definitions import definitions
from app.generic.issuer import issuer
from app.generic.wallet import wallets

logger = logging.getLogger(__name__)
prod = strtobool(os.environ.get("prod", "True"))
app = FastAPI(debug=not prod)

app.include_router(connections.router)
app.include_router(issuer.router)
app.include_router(messaging.router)
app.include_router(wallets.router)
app.include_router(wallet_admin.router)
app.include_router(schemas.router)
app.include_router(credential_definitions.router)
app.include_router(trust_registry.router)
app.include_router(definitions.router)


# add endpoints
# additional yaml version of openapi.json
@app.get("/openapi.yaml", include_in_schema=False)
def read_openapi_yaml() -> Response:
    openapi_json = app.openapi()
    yaml_s = io.StringIO()
    yaml.dump(openapi_json, yaml_s, allow_unicode=True, sort_keys=False)
    return Response(content=yaml_s.getvalue(), media_type="text/yaml")


@app.exception_handler(ClientResponseError)
async def client_response_error_exception_handler(
    request: Request, exc: ClientResponseError
):
    """This is the handler for handling the ClientResponseError

    that is the error fired by the aries cloud controller.
    It converts this erro into a nice json response which indicates the status and the
    message
    """
    if exc.status == 401:
        return JSONResponse(
            status_code=exc.status,
            content={"error_message": "401 Unauthorized"},
        )
    else:
        return JSONResponse(
            status_code=exc.status,
            content={"error_message": exc.message},
        )
