from typing import Literal, Optional

import httpx
from aries_cloudcontroller import AcaPyClient
from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.services import acapy_wallet
from app.services.acapy_ledger import accept_taa_if_required
from shared import LEDGER_REGISTRATION_URL, LEDGER_TYPE
from shared.log_config import get_logger

logger = get_logger(__name__)


class LedgerRequestSovrin(BaseModel):
    network: str = Field(None)
    did: str = Field(None)
    verkey: str = Field(None)
    payment_address: str = Field(None, alias="paymentaddr")


class LedgerRequestVon(BaseModel):
    did: str = Field(None)
    seed: str = Field(None)
    verkey: str = Field(None)
    role: str = Field(None)


async def post_to_ledger(
    did: str, verkey: str, role: Optional[Literal["ENDORSER"]] = "ENDORSER"
):
    if LEDGER_TYPE == "sovrin":
        payload = LedgerRequestSovrin(
            network="stagingnet",
            did=did,
            verkey=verkey,
        )
    elif LEDGER_TYPE == "von":
        payload = LedgerRequestVon(did=did, seed="null", verkey=verkey, role=role)
    else:
        raise HTTPException(
            status_code=501,
            detail="Cannot resolve ledger type. Should be either von or sovrin",
        )

    logger.info(f"Try post to ledger: {payload}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                LEDGER_REGISTRATION_URL, json=payload.model_dump(), timeout=300
            )
    except httpx.HTTPError as e:
        raise e from e

    if response.is_error:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Something went wrong.\nCould not write to Ledger.\n{response.text}",
        )
    logger.info("Successfully posted to ledger.")


async def has_public_did(aries_controller: AcaPyClient):
    try:
        await acapy_wallet.get_public_did(aries_controller)
        return True
    except Exception:
        return False


async def create_public_did(
    aries_controller: AcaPyClient, set_public: bool = True
) -> acapy_wallet.Did:
    logger.info("Handling create public did request")
    did_object = await acapy_wallet.create_did(aries_controller)

    if not did_object.did or not did_object.verkey:
        raise Exception("Cannot register did without did and/or verkey")

    await post_to_ledger(did=did_object.did, verkey=did_object.verkey)
    await accept_taa_if_required(aries_controller)

    if set_public:
        await acapy_wallet.set_public_did(aries_controller, did_object.did)

    logger.info("Successfully handled create public did request.")
    return did_object
