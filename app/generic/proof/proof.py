import logging
from enum import Enum
from typing import Optional

from fastapi import APIRouter
from generic.proof.facades.acapy_proof_v1 import ProofsV1
from generic.proof.facades.acapy_proof_v2 import ProofsV2
from pydantic.main import BaseModel
from typing_extensions import TypedDict

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/generic/proof/", tags=["proof"])


@router.post("/send-request")
async def send_proof_request():
    pass


@router.post("/create-request")
async def create_proof_request():
    pass


@router.get("/accept-request")
async def accept_proof_request():
    pass


@router.get("/reject-request")
async def reject_proof_request():
    pass
