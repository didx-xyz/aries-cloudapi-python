from admin.governance import dids
from fastapi import FastAPI
from routers import issuer, schema, verifier, wallet

app = FastAPI()


app.include_router(dids.router)
app.include_router(schema.router)
app.include_router(wallet.router)
app.include_router(verifier.router)
app.include_router(issuer.router)


@app.get("/")
async def root():
    return {"message": "Hi, and welcome to the Aries Cloud API."}
