import logging
import os


import requests
from fastapi import HTTPException

from schemas import LedgerRequestSovrin, LedgerRequestVon

LEDGER_URL = os.getenv("LEDGER_NETWORK_URL", "http://testnet.didx.xyz/register")
LEDGER_TYPE = os.getenv("LEDGER_TYPE")

logger = logging.getLogger(__name__)


async def _post_to_ledger(payload, url: str):
    """
    Post the did payload to the ledger

    Parameters:
    -----------
    url: str
        The url of the ledger to post to
    payload: dict
        The payload to be posted of the form:
        {
            "network": "stagingnet",
            "did": did_object["did"],
            "verkey": did_object["verkey"],
            "paymentaddr": "somestring",
        }

    Returns:
    --------
    post_to_ledger_resp: dict
        The response object of the post request
    """
    url = url if url else LEDGER_URL
    post_to_ledger_resp = requests.post(url, data=payload.json(), headers={})

    if post_to_ledger_resp.status_code != 200:
        error_json = post_to_ledger_resp.json()
        logger.error(f"Failed to write to ledger:\n{error_json}")
        raise HTTPException(
            status_code=post_to_ledger_resp.status_code,
            detail=f"Something went wrong.\nCould not write to Ledger.\n{error_json}",
        )

    ledger_post_res = {
        "status_code": post_to_ledger_resp.status_code,
        "headers": post_to_ledger_resp.headers,
        "res_obj": post_to_ledger_resp.json(),
    }
    return ledger_post_res


async def post_to_ledger(did_object=None, ledger_url=None, did=None, verkey=None):
    if did_object:
        did = did_object["did"]
        verkey = did_object["verkey"]

    if LEDGER_TYPE == "sovrin":
        payload = LedgerRequestSovrin(
            network="stagingnet",
            did=did,
            verkey=verkey,
            paymentaddr="",
        )
    elif LEDGER_TYPE == "von":
        payload = LedgerRequestVon(
            did=did,
            seed="null",
            verkey=verkey,
        )
    else:
        raise HTTPException(
            status_code=501,
            detail="Cannot resolve ledger type. Should be either von or sovrin",
        )
    await _post_to_ledger(payload, ledger_url)
