import logging
import os
from typing import Generic, TypeVar, Callable

from fastapi import HTTPException, Header


from enum import Enum

import logging
import os
import re
from typing import Type, Union, List

from aries_cloudcontroller import AriesAgentController, AriesTenantController
from fastapi import HTTPException

logger = logging.getLogger(__name__)

EXTRACT_TOKEN_FROM_BEARER = r"Bearer (.*)"

yoma_agent_url = os.getenv("ACAPY_YOMA_AGENT_URL", "http://localhost:3021")
ecosystem_agent_url = os.getenv("ACAPY_ECOSYSTEM_AGENT_URL", "http://localhost:4021")
member_agent_url = os.getenv("ACAPY_MEMBER_AGENT_URL", "http://localhost:4021")

embedded_api_key = os.getenv("EMBEDDED_API_KEY", "adminApiKey")


class ControllerType(Enum):
    YOMA_AGENT = "yoma_agent"
    MEMBER_AGENT = "member_agent"
    ECOSYSTEM_AGENT = "ecosystem_agent"


# apologies for the duplication here - removing this duplication introduces _way_ more complexity than it's worth
# I hope sonar does not bleat!


async def yoma_agent(x_api_key: str = Header(None), authorization: str = Header(None)):
    agent = None
    try:
        agent = _controller_factory(ControllerType.YOMA_AGENT, x_api_key, authorization)
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
    x_api_key: str = Header(None), authorization: str = Header(None)
):
    agent = None
    try:
        agent = _controller_factory(
            ControllerType.ECOSYSTEM_AGENT, x_api_key, authorization
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
    x_api_key: str = Header(None), authorization: str = Header(None)
):
    agent = None
    try:
        agent = _controller_factory(
            ControllerType.MEMBER_AGENT, x_api_key, authorization
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


def _controller_factory(
    controller_type: ControllerType,
    x_api_key=None,
    authorization_header=None,
    x_wallet_id=None,
) -> Type[Union[AriesAgentController, AriesTenantController]]:
    """
    Aries Controller factory returning an
    AriesController object based on a request header

    Parameters:
    -----------
    auth_headers: dict
        The header object containing wallet_id and jwt_token, or api_key

    Returns:
    --------
    controller: AriesCloudController (object)
    """
    if not controller_type:
        raise HTTPException(
            status_code=400,
            detail="Bad headers. Either provide an api_key or both wallet_id and tenant_jwt",
        )
    if controller_type == ControllerType.YOMA_AGENT:
        if not x_api_key:
            raise HTTPException(401)
        return AriesAgentController(
            admin_url=yoma_agent_url,
            api_key=x_api_key,
            is_multitenant=False,
        )
    elif controller_type == ControllerType.MEMBER_AGENT:
        if not authorization_header:
            raise HTTPException(401)
        return AriesTenantController(
            admin_url=member_agent_url,
            api_key=embedded_api_key,
            tenant_jwt=_extract_jwt_token_from_security_header(authorization_header),
            wallet_id=x_wallet_id,
        )
    elif controller_type == ControllerType.ECOSYSTEM_AGENT:
        if not authorization_header:
            raise HTTPException(401)
        return AriesTenantController(
            admin_url=ecosystem_agent_url,
            api_key=embedded_api_key,
            tenant_jwt=_extract_jwt_token_from_security_header(authorization_header),
            wallet_id=x_wallet_id,
        )
