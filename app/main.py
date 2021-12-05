import io
import logging
import os
import asyncio
import threading
from distutils.util import strtobool
from aries_cloudcontroller.acapy_client import AcaPyClient
from fastapi.exceptions import HTTPException
from starlette.responses import JSONResponse

import yaml
from fastapi import FastAPI, Request, Response

from app.admin.governance import credential_definitions, schemas
from app.admin.governance.multitenant_wallet import wallet_admin
from app.constants import YOMA_AGENT_URL
from app.facades.acapy_ledger import accept_taa_if_required
from app.facades.acapy_wallet import get_pub_did, get_public_did
from app.generic import messaging, trust_registry
from app.generic.connections import connections
from app.generic.issuer import issuer
from app.generic.verifier import verifier
from app.generic.wallet import wallets
from app.generic.definitions import definitions

logger = logging.getLogger(__name__)
prod = strtobool(os.environ.get("prod", "True"))
app = FastAPI(debug=not prod)

app.include_router(connections.router)
app.include_router(issuer.router)
app.include_router(messaging.router)
app.include_router(wallets.router)
app.include_router(wallet_admin.router)
app.include_router(verifier.router)
app.include_router(schemas.router)
app.include_router(credential_definitions.router)
app.include_router(definitions.router)
app.include_router(trust_registry.router)


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
    if not isinstance(exception, HTTPException):
        return JSONResponse({"detail": f"Error processing request:"}, 500)
    else:
        return JSONResponse(exception.detail, exception.status_code, exception.headers)


@app.on_event("startup")
async def startup_event():
    print("Setting up Yoma agent")
    client = AcaPyClient(YOMA_AGENT_URL, api_key="adminApiKey")

    for _ in range(5):
        print("try")
        try:
            is_ready = await client.server.get_ready_state()

            if is_ready.ready:
                print("accept taa if required")
                await accept_taa_if_required(client)
                # FIXME: will throw
                public_did = await get_public_did(client)
                did = "d"
                await client.wallet.set_public_did(did=did)
                return
        except:
            pass

        await asyncio.sleep(5)

    raise Exception("Agent is not ready")
