import logging
import traceback
from typing import List, Optional

from fastapi import APIRouter, Header

from facade import(
    create_controller,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/verifier")

#TODO verify that active connection exists
#Better tag?
@router.get("/create-proof-request", tags=["proof"])
async def get_proof_request(req_header: Optional[str] = Header(None), schema_id:str, revocation:bool, ):

    try:
        async with create_controller(req_header) as controller:

