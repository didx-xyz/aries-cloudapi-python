from fastapi import Depends, FastAPI

from admin import admin
from routers import holder, issuer, verifier, wallet

app = FastAPI(dependencies=[Depends(get_query_token)])


app.include_routers(wallet.router)
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