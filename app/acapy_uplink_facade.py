from typing import List

from pydantic import BaseModel, Field
from uplink import Consumer, get, Header, returns, Body, json
import uplink


class WalletDids(BaseModel):
    verkey: str
    did: str
    posture: str


class WalletDidsResponse(BaseModel):
    results: List[WalletDids]


class Schema(BaseModel):
    schema_version: str
    attributes: List[str]
    schema_name: str


class SchemaCreated(BaseModel):
    ver: str
    attrNames: List[str]
    name: str
    version: str
    id: str
    seqNo: int


class SchemaSendResults(BaseModel):
    schema_id: str
    schema_: SchemaCreated = Field(alias="schema")


class AcapyWallet(Consumer):
    """A Python Client for the GitHub API."""

    @uplink.get("wallet/did")
    def get_wallet_dids(self, x_api_key: Header("x-api-key")) -> WalletDidsResponse:
        """Get Wallet Dids"""


class AcapySchemas(Consumer):
    @uplink.json
    @uplink.headers({"content-type": "application/json"})
    @uplink.post("schemas")
    def create_schema(
        self, schema: Body, x_api_key: Header("x-api-key")
    ) -> SchemaSendResults:
        """create a schema"""
