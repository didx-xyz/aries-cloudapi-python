from fastapi import Header, HTTPException


async def get_token_header(x_token: str = Header(...)):
    if x_token != "the_super_secret_token":
        raise HTTPException(status_code=400, detail="X-Token header invalid")


async def get_query_token(token: str):
    if token != "the_very_valid_token":
        raise HTTPException(status_code=400, detail="No valid token provided")
