from distutils.util import strtobool
import os
import io

from fastapi import FastAPI, Response
import yaml


from routers import issuer, schema, verifier
from admin.governance import schemas, credential_definitions
from admin.governance.multitenant_wallet import wallet
from admin.governance import dids
from admin.governance import credential_definitions, dids, schemas
from fastapi import FastAPI
from generic import connections
from routers import issuer, schema, verifier
from admin.governance.multitenant_wallet import wallet_admin
from admin.governance.wallet import wallets

prod = strtobool(os.environ.get("prod", "False"))
app = FastAPI(debug=not prod)

app.include_router(connections.router)
app.include_router(dids.router)
app.include_router(schemas.router)
app.include_router(credential_definitions.router)
app.include_router(wallet_admin.router)
app.include_router(verifier.router)
app.include_router(issuer.router)
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
