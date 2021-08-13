from aiohttp import ClientResponseError
from distutils.util import strtobool
import os
import io
import yaml

from fastapi import FastAPI, Response, Request
from fastapi.responses import JSONResponse

from admin.governance import credential_definitions, dids, schemas
from fastapi import FastAPI
from generic import connections, issuers_v1, issuer_v2, messaging
from routers import issuer, verifier
from admin.governance.multitenant_wallet import wallet_admin
from generic.wallet import wallets


prod = strtobool(os.environ.get("prod", "True"))
app = FastAPI(debug=not prod)

app.include_router(connections.router)
app.include_router(credential_definitions.router)
app.include_router(dids.router)
app.include_router(issuer_v2.router)
app.include_router(issuers_v1.router)
app.include_router(messaging.router)
app.include_router(schemas.router)
app.include_router(verifier.router)
app.include_router(wallet_admin.router)
app.include_router(wallets.router)


@app.get("/", tags=["Root"])
async def root():
    return {"message": "Hi, and welcome to the Aries Cloud API."}


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
