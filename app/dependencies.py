from fastapi import Header

import logging
import os
import re

from aries_cloudcontroller import AriesAgentController, AriesTenantController
from fastapi import HTTPException

logger = logging.getLogger(__name__)

EXTRACT_TOKEN_FROM_BEARER = r"Bearer (.*)"

YOMA_AGENT_URL = os.getenv("ACAPY_YOMA_AGENT_URL", "http://localhost:3021")
ECOSYSTEM_AGENT_URL = os.getenv("ACAPY_ECOSYSTEM_AGENT_URL", "http://localhost:4021")
MEMBER_AGENT_URL = os.getenv("ACAPY_MEMBER_AGENT_URL", "http://localhost:4021")

EMBEDDED_API_KEY = os.getenv("EMBEDDED_API_KEY", "adminApiKey")


async def yoma_agent(x_api_key: str = Header(None)):
    agent = None
    try:
        if not x_api_key:
            raise HTTPException(401)
        agent = AriesAgentController(
            admin_url=YOMA_AGENT_URL,
            api_key=x_api_key,
            is_multitenant=False,
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


async def ecosystem_agent(
    x_api_key: str = Header(None),
    authorization: str = Header(None),
    x_wallet_id=Header(None),
):
    agent = None
    try:
        # TODO extract wallet_id instead of passing it?!

        # check the header is present
        if not authorization:
            raise HTTPException(401)

        # extract the JWT
        tenant_jwt = _extract_jwt_token_from_security_header(authorization)

        # yield the controller
        agent = AriesTenantController(
            admin_url=ECOSYSTEM_AGENT_URL,
            api_key=x_api_key,
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
        if not authorization:
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
        if not x_api_key:
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
        if not x_api_key:
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
