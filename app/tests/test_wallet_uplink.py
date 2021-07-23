from traceback import print_exc

import aiohttp
import pytest
import uplink
from aiohttp import ClientSession, TraceRequestChunkSentParams, ClientResponseError

from api import WalletApi, DIDCreate


@pytest.mark.asyncio
async def test_list_dids():
    async with ClientSession(headers={"x-api-key": "adminApiKey"}) as session:
        wallet_api = WalletApi(
            base_url="http://localhost:3021", client=uplink.AiohttpClient(session)
        )
        did_list = await wallet_api.list_dids()
        print(did_list)


async def on_request_start(session, context, params):
    print(f"Starting request <{params}>")


async def on_signal(session, context, params: TraceRequestChunkSentParams):
    print(f"chunk: <{params.chunk}>")


async def on_event(session, context, params):
    print(f"on event <{params}>")


@pytest.mark.asyncio
async def test_create_default_did():
    trace_config = aiohttp.TraceConfig()
    trace_config.on_request_start.append(on_request_start)
    trace_config.on_request_chunk_sent.append(on_signal)
    trace_config.on_response_chunk_received.append(on_signal)
    async with ClientSession(
        headers={"x-api-key": "adminApiKey"},
        trace_configs=[trace_config],
        raise_for_status=True,
    ) as session:
        wallet_api = WalletApi(
            base_url="http://localhost:3021", client=uplink.AiohttpClient(session)
        )
        try:
            did_list = await wallet_api.create_default_did()
            print(did_list)
        except ClientResponseError as e:
            print_exc()
            print(e)


@pytest.mark.asyncio
async def test_create_did():
    trace_config = aiohttp.TraceConfig()
    trace_config.on_request_start.append(on_request_start)
    trace_config.on_request_chunk_sent.append(on_signal)
    trace_config.on_response_chunk_received.append(on_signal)
    async with ClientSession(
        headers={"x-api-key": "adminApiKey"},
        trace_configs=[trace_config],
        raise_for_status=True,
    ) as session:
        wallet_api = WalletApi(
            base_url="http://localhost:3021", client=uplink.AiohttpClient(session)
        )
        try:
            did_list = await wallet_api.create_did(DIDCreate(method="keyx"))
            print(did_list)
        except ClientResponseError as e:
            print_exc()
            print(e)
