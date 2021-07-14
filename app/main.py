from admin.governance import credential_definitions, dids, schemas
from admin.governance.multitenant_wallet import wallet
from fastapi import FastAPI
from generic import connections
from routers import issuer, schema, verifier

app = FastAPI()


app.include_router(connections.router)
app.include_router(dids.router)
app.include_router(schema.router)
app.include_router(schemas.router)
app.include_router(credential_definitions.router)
app.include_router(wallet.router)
app.include_router(verifier.router)
app.include_router(issuer.router)


@app.get("/")
async def root():
    return {"message": "Hi, and welcome to the Aries Cloud API."}
