import os

import json

import requests
from fastapi import HTTPException

from schemas import LedgerRequest

SOVRIN_NETWORK = os.getenv("SOVRIN_NETWORK", "stagingnet")

ledger_url = os.getenv("LEDGER_NETWORK_URL")

async def get_nym(did_object=None, did=None, verkey=None):
    # TODO: not sure what this method should be called... please help
    # TODO: Network and paymentaddr should be definable on the fly/via args/via request body
    # TODO: Should this really be a schema or is using schema overkill here?
    # If we leave it as schema like this I suppose it is at least usable elsewhere
    if did_object:
        did = did_object["did"]
        verkey = did_object["verkey"]
    payload = LedgerRequest(
        network=SOVRIN_NETWORK,
        did=did,
        verkey=verkey,
        paymentaddr="",
    ).dict()
    r = requests.post(ledger_url, data=json.dumps(payload), headers={})
    if r.status_code != 200:
        error_json = r.json()
        raise HTTPException(
            status_code=r.status_code,
            detail=f"Something went wrong.\nCould not write to StagingNet.\n{error_json}",
        )
    return r



