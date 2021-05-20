from fastapi import Depends, FastAPI

from dependencies import get_query_token, get_token_header
from admin import admin
from routers import holder, issuer, verifier, wallet, schema, governance

# app = FastAPI(dependencies=[Depends(get_query_token)])
app = FastAPI()


app.include_router(wallet.router)
app.include_router(schema.router)
app.include_router(governance.router)
app.include_router(
    admin.router,
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_token_header)],
    responses={418: {"description": "I'm a teapot"}},
)


@app.get("/")
async def root():
    return {"message": "Hi, and welcome to the Aries Cloud API."}
