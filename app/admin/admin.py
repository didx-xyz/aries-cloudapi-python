from fastapi import APIRouter

router = APIRouter()


@router.get("/", tags=["admin"])
async def admin_root():
    return {"message": "Hello from the admin controller"}
