import json
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


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
    schema_version: str
    schema_attrs: List[str]


class SchemaResponse(BaseModel):
    schema_resp: dict
    schema_id: str
    credential_definition: dict
    credential_definition_id: str


class InitWalletRequest(BaseModel):
    image_url: Optional[str] = "https://aries.ca/images/sample.png"
    key_management_mode: Optional[str] = "managed"
    label: str
    wallet_dispatch_type: Optional[str] = "default"
    wallet_key: str
    wallet_name: str
    wallet_type: Optional[str] = "indy"

    class Config:
        schema_extra = {
            "example": {
                "image_url": "https://aries.ca/images/sample.png",
                "key_management_mode": "managed",
                "label": "Alice",
                "wallet_dispatch_type": "default",
                "wallet_key": "MySecretKey1234",
                "wallet_name": "AlicesWallet",
                "wallet_type": "indy",
            }
        }
