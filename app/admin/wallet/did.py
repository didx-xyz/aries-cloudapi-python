import logging
import traceback
from typing import Optional

from fastapi import APIRouter, Header

from utils import create_pub_did

from schemas import (
    DidCreationResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/wallet", tags=["admin", "wallet"])


@router.get("/assign-pub-did", tags=["did"], response_model=DidCreationResponse)
async def create_public_did(
    api_key: Optional[str] = Header(None),
):
    """
    Create a new public DID and
    write it to the ledger and
    receive its public info.

    Parameters:
    -----------
    api_key: Header(None)
        The request header object api_key

    Returns:
    * DID object (json)
    * Issuer verkey (str)
    * Issuer Endpoint (url)
    """
    auth_headers = {
        "api_key": api_key,
        "wallet_id": None,
        "tenant_jwt": None,
    }
    try:
        return await create_pub_did(auth_headers)
    except Exception as e:
        err_trace = traceback.print_exc()
        logger.error(
            f"Failed to create public DID. The following error occured:\n{e!r}\n{err_trace}"
        )
        raise e
