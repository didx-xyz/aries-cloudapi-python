import json
from typing import Optional, List

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


class SchemaLedgerRequest(BaseModel):
    schema_name: str
    schema_version : str
    schema_attrs: List[str]

class SchemaResponse(BaseModel):
    schema: str
    schema_id : str
    credential_definition : str
    credential_id : str