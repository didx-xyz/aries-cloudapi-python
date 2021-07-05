from admin.governance import schemas, credential_definitions
from fastapi import FastAPI
from routers import issuer, verifier, wallet

app = FastAPI()

app.include_router(schemas.router)
app.include_router(credential_definitions.router)
app.include_router(wallet.router)
app.include_router(verifier.router)
app.include_router(issuer.router)


@app.get("/")
async def root():
    return {"message": "Hi, and welcome to the Aries Cloud API."}
