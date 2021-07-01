import pytest
import unittest
from aiohttp import ClientSession
from uplink import AiohttpClient

from acapy_uplink_facade import AcapyWallet, AcapySchemas, Schema


@pytest.mark.asyncio
async def test_list_public_dids():
    async with ClientSession() as session:
        wallet = AcapyWallet(base_url="http://localhost:3021", client=session)
        result = await wallet.get_wallet_dids(x_api_key="adminApiKey")
        print(result)


@pytest.mark.asyncio
async def test_create_schema():
    async with ClientSession() as session:
        schemas = AcapySchemas(base_url="http://localhost:3021", client=session)
        schema = Schema(
            schema_version="1.0",
            schema_name="deafult_test",
            attributes=["name", "dateofbirth"],
        )
        result = await schemas.create_schema(
            schema=schema.dict(), x_api_key="adminApiKey"
        )
        print(result)
