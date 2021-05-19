from fastapi import APIRouter, HTTPException

import aries_cloudcontroller

router = APIRouter()

@router.get("/issuer/issue-credential",tags=["issue","credential"])
async def issue_credential()