import logging
import os
import re
from contextlib import asynccontextmanager

from aries_cloudcontroller import AcaPyClient
from fastapi import Header, HTTPException

logger = logging.getLogger(__name__)

EXTRACT_TOKEN_FROM_BEARER = r"Bearer (.*)"

YOMA_AGENT_URL = os.getenv("ACAPY_YOMA_AGENT_URL", "http://localhost:3021")
ECOSYSTEM_AGENT_URL = os.getenv("ACAPY_ECOSYSTEM_AGENT_URL", "http://localhost:4021")
MEMBER_AGENT_URL = os.getenv("ACAPY_MEMBER_AGENT_URL", "http://localhost:4021")

EMBEDDED_API_KEY = os.getenv("EMBEDDED_API_KEY", "adminApiKey")


async def yoma_agent(x_api_key: str = Header(None)):
    agent = None
    try:
        if str(x_api_key) == "extra={}":
            raise HTTPException(401)
        agent = AcaPyClient(
            YOMA_AGENT_URL, api_key=x_api_key, admin_insecure=x_api_key == None
        )
        yield agent
    except Exception as e:
        # We can only log this here and not raise an HTTPExeption as
        # we are past the yield. See here: https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/#dependencies-with-yield-and-httpexception
        logger.error("%s", e, exc_info=e)
        raise e
    finally:
        if agent:
            await agent.close()


async def agent_selector(
    x_api_key: str = Header(None),
    x_auth: str = Header(None),
    x_wallet_id=Header(None),
    x_role=Header(...),
):
    if x_role == "member":
        async with asynccontextmanager(member_agent)(x_auth, x_wallet_id) as x:
            yield x
    elif (
        x_role == "eco-system" or x_role == "ecosystem"
    ):  # cannot use in as it's not a string
        async with asynccontextmanager(ecosystem_agent)(
            x_api_key, x_auth, x_wallet_id
        ) as x:
            yield x
    elif x_role == "yoma":
        async with asynccontextmanager(yoma_agent)(x_api_key) as x:
            yield x
    else:
        raise HTTPException(400, "invalid role")


async def admin_agent_selector(
    x_api_key: str = Header(None),
    x_auth: str = Header(None),
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
    x_auth: str = Header(None),
    x_wallet_id=Header(None),
):
    agent = None
    try:
        # TODO extract wallet_id instead of passing it?!

        # check the header is present
        if str(x_auth) == "extra={}":
            raise HTTPException(401)

        # extract the JWT
        tenant_jwt = _extract_jwt_token_from_security_header(x_auth)

        # yield the controller
        agent = AcaPyClient(
            ECOSYSTEM_AGENT_URL,
            api_key=EMBEDDED_API_KEY,
            tenant_jwt=tenant_jwt,
            admin_insecure=x_api_key == None
            # TODO: where is the wallet id used (webhooks?)
            # wallet_id=x_wallet_id,
        )
        yield agent
    except Exception as e:
        # We can only log this here and not raise an HTTPExeption as
        # we are past the yield. See here: https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/#dependencies-with-yield-and-httpexception
        logger.error("%s", e, exc_info=e)
        raise e
    finally:
        if agent:
            await agent.close()


async def member_agent(
    x_auth: str = Header(None),
    x_wallet_id=Header(None),
):
    agent = None
    try:
        if str(x_auth) == "extra={}":
            raise HTTPException(401)
        tenant_jwt = _extract_jwt_token_from_security_header(x_auth)
        agent = AcaPyClient(
            base_url=MEMBER_AGENT_URL,
            api_key=EMBEDDED_API_KEY,
            tenant_jwt=tenant_jwt,
            # TODO: where is the wallet id used (webhooks?)
            # wallet_id=x_wallet_id,
        )
        yield agent
    except Exception as e:
        # We can only log this here and not raise an HTTPExeption as
        # we are past the yield. See here: https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/#dependencies-with-yield-and-httpexception
        logger.error("%s", e, exc_info=e)
        raise e
    finally:
        if agent:
            await agent.close()


async def member_admin_agent(
    x_api_key: str = Header(None),
):
    agent = None
    try:
        if str(x_api_key) == "extra={}":
            raise HTTPException(401)
        agent = AcaPyClient(
            MEMBER_AGENT_URL, api_key=x_api_key, admin_insecure=x_api_key == None
        )
        yield agent
    except Exception as e:
        # We can only log this here and not raise an HTTPExeption as
        # we are past the yield. See here: https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/#dependencies-with-yield-and-httpexception
        logger.error("%s", e, exc_info=e)
        raise e
    finally:
        if agent:
            await agent.close()


async def ecosystem_admin_agent(
    x_api_key: str = Header(None),
):
    agent = None
    try:
        if str(x_api_key) == "extra={}":
            raise HTTPException(401)
        agent = AcaPyClient(
            base_url=ECOSYSTEM_AGENT_URL,
            api_key=x_api_key,
            admin_insecure=x_api_key == None,
        )
        yield agent
    except Exception as e:
        # We can only log this here and not raise an HTTPExeption as
        # we are past the yield. See here: https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/#dependencies-with-yield-and-httpexception
        logger.error("%s", e, exc_info=e)
        raise e
    finally:
        if agent:
            await agent.close()


def _extract_jwt_token_from_security_header(jwt_token):
    if not jwt_token:
        raise HTTPException(401)
    x = re.search(EXTRACT_TOKEN_FROM_BEARER, jwt_token)
    if x is not None:
        return x.group(1)
    else:
        raise HTTPException(401)
