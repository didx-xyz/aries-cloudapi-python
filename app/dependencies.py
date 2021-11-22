import logging
import os
import re
from contextlib import asynccontextmanager

from aries_cloudcontroller import AcaPyClient
from fastapi import Header, HTTPException
from fastapi.params import Depends
from fastapi.security import APIKeyHeader, HTTPBearer

logger = logging.getLogger(__name__)

EXTRACT_TOKEN_FROM_BEARER = r"Bearer (.*)"

YOMA_AGENT_URL = os.getenv("ACAPY_YOMA_AGENT_URL", "http://localhost:3021")
ECOSYSTEM_AGENT_URL = os.getenv("ACAPY_ECOSYSTEM_AGENT_URL", "http://localhost:4021")
MEMBER_AGENT_URL = os.getenv("ACAPY_MEMBER_AGENT_URL", "http://localhost:4021")

EMBEDDED_API_KEY = os.getenv("EMBEDDED_API_KEY", "adminApiKey")

x_api_key_scheme = APIKeyHeader(name="x-api-key")
authorization_optional = HTTPBearer(auto_error=False)
authorization_required = HTTPBearer(auto_error=True)


async def yoma_agent(x_api_key: str = Depends(x_api_key_scheme)):
    agent = None
    try:
        if str(x_api_key) == "extra={}":
            raise HTTPException(401)
        agent = AcaPyClient(YOMA_AGENT_URL, api_key=x_api_key)
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
    authorization: str = Depends(authorization_optional),
    x_api_key: str = Depends(x_api_key_scheme),
    x_role: str = Header(...),
):
    if not x_api_key and not authorization:
        raise HTTPException(400, "API key or JWT required for auth.")
    if x_role == "member":
        async with asynccontextmanager(member_agent)(authorization) as x:
            yield x
    elif (
        x_role == "eco-system" or x_role == "ecosystem"
    ):  # cannot use in as it's not a string
        async with asynccontextmanager(ecosystem_agent)(authorization) as x:
            yield x
    elif x_role == "yoma":
        async with asynccontextmanager(yoma_agent)(x_api_key) as x:
            yield x
    else:
        raise HTTPException(400, "invalid role")


async def admin_agent_selector(
    x_api_key: str = Depends(x_api_key_scheme),
    x_role: str = Header(...),
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
    authorization: str = Depends(authorization_required),
):
    agent = None
    try:
        # check the header is present
        if str(authorization) == "extra={}":
            raise HTTPException(401)

        # extract the JWT
        tenant_jwt = _extract_jwt_token_from_security_header(authorization)

        # yield the controller
        agent = AcaPyClient(
            base_url=ECOSYSTEM_AGENT_URL,
            api_key=EMBEDDED_API_KEY,
            tenant_jwt=tenant_jwt,
        )
        yield agent
    except Exception as e:
        # We can only log this here and not raise an HTTPException as
        # we are past the yield. See here: https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/#dependencies-with-yield-and-httpexception
        logger.error("%s", e, exc_info=e)
        raise e
    finally:
        if agent:
            await agent.close()


async def member_agent(
    authorization: str = Depends(authorization_required),
):
    agent = None
    try:
        if str(authorization) == "extra={}":
            raise HTTPException(401)
        tenant_jwt = _extract_jwt_token_from_security_header(authorization)
        agent = AcaPyClient(
            base_url=MEMBER_AGENT_URL,
            api_key=EMBEDDED_API_KEY,
            tenant_jwt=tenant_jwt,
        )
        yield agent
    except Exception as e:
        # We can only log this here and not raise an HTTPException as
        # we are past the yield. See here: https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/#dependencies-with-yield-and-httpexception
        logger.error("%s", e, exc_info=e)
        raise e
    finally:
        if agent:
            await agent.close()


async def member_admin_agent(x_api_key: str = Depends(x_api_key_scheme)):
    agent = None
    try:
        if str(x_api_key) == "extra={}":
            raise HTTPException(401)
        agent = AcaPyClient(
            base_url=MEMBER_AGENT_URL,
            api_key=x_api_key,
            admin_insecure=True,
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


async def ecosystem_admin_agent(x_api_key: str = Depends(x_api_key_scheme)):
    agent = None
    try:
        if str(x_api_key) == "extra={}":
            raise HTTPException(401)
        agent = AcaPyClient(
            base_url=ECOSYSTEM_AGENT_URL,
            api_key=x_api_key,
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
