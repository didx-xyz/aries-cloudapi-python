import json
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, Json


# TODO what is a good name for this
# TODO should this really be a schema
class LedgerRequest(BaseModel):
    network: str = Field(None)
    did: str = Field(None)
    verkey: str = Field(None)
    paymentaddr: str = Field(None)


class DidCreationResponse(BaseModel):
    did_object: dict
    issuer_verkey: str
    issuer_endpoint: str
