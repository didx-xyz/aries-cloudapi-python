from fastapi import APIRouter

router = APIRouter()

@router.get("/wallets/", tags=["wallets"])
async def wallets_root():
    return {"message": "Hello from the wallets controller"}