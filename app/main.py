from admin import admin
from fastapi import Depends, FastAPI
from routers import governance, holder, issuer, schema, verifier
from admin.governance.multitenant_wallet import wallet
from admin.governance import dids

app = FastAPI()


app.include_router(dids.router)
app.include_router(schema.router)
app.include_router(wallet.router)
app.include_router(verifier.router)
app.include_router(issuer.router)


@app.get("/")
async def root():
    return {"message": "Hi, and welcome to the Aries Cloud API."}
