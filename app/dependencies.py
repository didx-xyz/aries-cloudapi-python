import logging
import os
import re
from contextlib import asynccontextmanager

import aiohttp
import uplink
from aiohttp import ClientSession, TraceRequestChunkSentParams
from aries_cloudcontroller import AriesAgentController, AriesTenantController
from fastapi import Header, HTTPException

from api import WalletApi

logger = logging.getLogger(__name__)

EXTRACT_TOKEN_FROM_BEARER = r"Bearer (.*)"

YOMA_AGENT_URL = os.getenv("ACAPY_YOMA_AGENT_URL", "http://localhost:3021")
ECOSYSTEM_AGENT_URL = os.getenv("ACAPY_ECOSYSTEM_AGENT_URL", "http://localhost:4021")
MEMBER_AGENT_URL = os.getenv("ACAPY_MEMBER_AGENT_URL", "http://localhost:4021")

EMBEDDED_API_KEY = os.getenv("EMBEDDED_API_KEY", "adminApiKey")


async def on_request_start(session, context, params):
    print(f"Starting request <{params}>")


async def on_signal(session, context, params: TraceRequestChunkSentParams):
    print(f"chunk: <{params.chunk}>")


async def on_event(session, context, params):
    print(f"on event <{params}>")


trace_config = aiohttp.TraceConfig()
trace_config.on_request_start.append(on_request_start)
trace_config.on_request_chunk_sent.append(on_signal)
trace_config.on_response_chunk_received.append(on_signal)


async def yoma_agent(x_api_key: str = Header(None)):
    agent = None
    try:
        if str(x_api_key) == "extra={}":
            raise HTTPException(401)
        agent = AriesAgentController(
            admin_url=YOMA_AGENT_URL,
            api_key=x_api_key,
            is_multitenant=False,
        )
        url = YOMA_AGENT_URL
        async with ClientSession(
            headers={"x-api-key": "adminApiKey"},
            trace_configs=[trace_config],
            raise_for_status=True,
        ) as session:
            wallet = WalletApi(base_url=url, client=uplink.AiohttpClient(session))
            agent.wallet = wallet
            yield agent

    except Exception as e:
        # We can only log this here and not raise an HTTPExeption as
        # we are past the yield. See here: https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/#dependencies-with-yield-and-httpexception
        logger.error("%s", e, exc_info=e)
        raise e
    finally:
        if agent:
            await agent.terminate()


async def create_agent(url, x_api_key):
    with ClientSession(headers={"x-api-key": x_api_key}) as session:
        wallet = WalletApi(base_url=url, client=uplink.AiohttpClient(session))
        agent = object()
        agent.wallet = wallet
        yield agent


async def create_agent0(agent, url, x_api_key):
    agent = AriesAgentController(
        admin_url=url,
        api_key=x_api_key,
        is_multitenant=False,
    )
    return agent


async def agent_selector(
    x_api_key: str = Header(None),
    authorization: str = Header(None),
    x_wallet_id=Header(None),
    x_role=Header(...),
):
    if x_role == "member":
        async with asynccontextmanager(member_agent)(authorization, x_wallet_id) as x:
            yield x
    elif (
        x_role == "eco-system" or x_role == "ecosystem"
    ):  # cannot use in as it's not a string
        async with asynccontextmanager(ecosystem_agent)(
            x_api_key, authorization, x_wallet_id
        ) as x:
            yield x
    elif x_role == "yoma":
        async with asynccontextmanager(yoma_agent)(x_api_key) as x:
            yield x
    else:
        raise HTTPException(400, "invalid role")


async def admin_agent_selector(
    x_api_key: str = Header(None),
    authorization: str = Header(None),
    x_wallet_id=Header(None),
    x_role=Header(...),
):
    if x_role == "member":
        async with asynccontextmanager(member_admin_agent)(x_api_key) as x:
            yield x
    elif x_role == "eco-system" or x_role == "ecosystem":
        async with asynccontextmanager(ecosystem_admin_agent)(x_api_key) as x:
            yield x
    elif x_role == "yoma":
        async with asynccontextmanager(yoma_agent)(x_api_key) as x:
            yield x
    else:
        raise HTTPException(400, "invalid role")


async def ecosystem_agent(
    x_api_key: str = Header(None),
    authorization: str = Header(None),
    x_wallet_id=Header(None),
):
    agent = None
    try:
        # TODO extract wallet_id instead of passing it?!

        # check the header is present
        if str(authorization) == "extra={}":
            raise HTTPException(401)

        # extract the JWT
        tenant_jwt = _extract_jwt_token_from_security_header(authorization)

        # yield the controller
        agent = AriesTenantController(
            admin_url=ECOSYSTEM_AGENT_URL,
            api_key=EMBEDDED_API_KEY,
            tenant_jwt=tenant_jwt,
            wallet_id=x_wallet_id,
        )
        yield agent
    except Exception as e:
        # We can only log this here and not raise an HTTPExeption as
        # we are past the yield. See here: https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/#dependencies-with-yield-and-httpexception
        logger.error("%s", e, exc_info=e)
        raise e
    finally:
        if agent:
            await agent.terminate()


async def member_agent(
    authorization: str = Header(None),
    x_wallet_id=Header(None),
):
    agent = None
    try:
        if str(authorization) == "extra={}":
            raise HTTPException(401)
        tenant_jwt = _extract_jwt_token_from_security_header(authorization)
        agent = AriesTenantController(
            admin_url=MEMBER_AGENT_URL,
            api_key=EMBEDDED_API_KEY,
            tenant_jwt=tenant_jwt,
            wallet_id=x_wallet_id,
        )
        yield agent
    except Exception as e:
        # We can only log this here and not raise an HTTPExeption as
        # we are past the yield. See here: https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/#dependencies-with-yield-and-httpexception
        logger.error("%s", e, exc_info=e)
        raise e
    finally:
        if agent:
            await agent.terminate()


async def member_admin_agent(
    x_api_key: str = Header(None),
):
    agent = None
    try:
        if str(x_api_key) == "extra={}":
            raise HTTPException(401)
        agent = AriesAgentController(
            admin_url=MEMBER_AGENT_URL, api_key=x_api_key, is_multitenant=True
        )
        yield agent
    except Exception as e:
        # We can only log this here and not raise an HTTPExeption as
        # we are past the yield. See here: https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/#dependencies-with-yield-and-httpexception
        logger.error("%s", e, exc_info=e)
        raise e
    finally:
        if agent:
            await agent.terminate()


async def ecosystem_admin_agent(
    x_api_key: str = Header(None),
):
    agent = None
    try:
        if str(x_api_key) == "extra={}":
            raise HTTPException(401)
        agent = AriesAgentController(
            admin_url=ECOSYSTEM_AGENT_URL, api_key=x_api_key, is_multitenant=True
        )
        yield agent
    except Exception as e:
        # We can only log this here and not raise an HTTPExeption as
        # we are past the yield. See here: https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/#dependencies-with-yield-and-httpexception
        logger.error("%s", e, exc_info=e)
        raise e
    finally:
        if agent:
            await agent.terminate()


def _extract_jwt_token_from_security_header(jwt_token):
    if not jwt_token:
        raise HTTPException(401)
    x = re.search(EXTRACT_TOKEN_FROM_BEARER, jwt_token)
    if x is not None:
        return x.group(1)
    else:
        raise HTTPException(401)
