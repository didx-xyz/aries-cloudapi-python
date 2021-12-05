from enum import Enum
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Callable, List, NamedTuple, Optional, Union

from aries_cloudcontroller import AcaPyClient
from fastapi import HTTPException
from fastapi.params import Depends
from fastapi.security import APIKeyHeader
from app.constants import (
    YOMA_AGENT_URL,
    ECOSYSTEM_AGENT_URL,
    MEMBER_AGENT_URL,
    EMBEDDED_API_KEY,
)

logger = logging.getLogger(__name__)


x_api_key_scheme = APIKeyHeader(name="x-api-key")


class AcaPyAuth:
    token: str
    role: "Role"

    def __init__(self, *, role: "Role", token: str) -> None:
        self.role = role
        self.token = token


def acapy_auth(auth: str = Depends(x_api_key_scheme)):
    [role_str, token] = auth.split(".", maxsplit=1)

    role = Role.from_str(role_str)

    if not role:
        raise HTTPException(401, "Unauthorized")

    return AcaPyAuth(role=role, token=token)


async def agent_selector(auth: AcaPyAuth = Depends(acapy_auth)):
    async with asynccontextmanager(auth.role.agent_type.agent_selector)(auth) as x:
        yield x


async def admin_agent_selector(auth: AcaPyAuth = Depends(acapy_auth)):
    if not auth.role.agent_type.is_admin:
        raise HTTPException(403, "Unauthorized")

    async with asynccontextmanager(auth.role.agent_type.agent_selector)(auth) as x:
        yield x


def agent_role(role: Union["Role", List["Role"]]):
    async def run(auth: AcaPyAuth = Depends(acapy_auth)):
        roles = role if isinstance(role, List) else [role]

        if auth.role not in roles:
            raise HTTPException(403, "Unauthorized")

        async with asynccontextmanager(auth.role.agent_type.agent_selector)(auth) as x:
            yield x

    return run


async def multitenant_agent(auth: AcaPyAuth = Depends(acapy_auth)):
    if not auth.token or auth.token == "":
        raise HTTPException(403, "Missing authorization key")

    agent = None
    try:
        # yield the controller
        agent = AcaPyClient(
            base_url=auth.role.agent_type.base_url,
            api_key=EMBEDDED_API_KEY,
            tenant_jwt=auth.token,
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


async def admin_agent(auth: AcaPyAuth = Depends(acapy_auth)):
    agent = None
    try:
        agent = AcaPyClient(auth.role.agent_type.base_url, api_key=auth.token)
        yield agent
    except Exception as e:
        # We can only log this here and not raise an HTTPException as
        # we are past the yield. See here: https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/#dependencies-with-yield-and-httpexception
        logger.error("%s", e, exc_info=e)
        raise e
    finally:
        if agent:
            await agent.close()


class AgentType(NamedTuple):
    name: str
    base_url: str
    agent_selector: Callable[["AcaPyAuth"], AsyncGenerator[AcaPyClient, None]]
    is_admin: bool


class Role(Enum):
    YOMA = AgentType("yoma", YOMA_AGENT_URL, admin_agent, True)
    ECOSYSTEM = AgentType("ecosystem", ECOSYSTEM_AGENT_URL, multitenant_agent, False)
    ECOSYSTEM_ADMIN = AgentType(
        "ecosystem-admin", ECOSYSTEM_AGENT_URL, admin_agent, True
    )
    MEMBER = AgentType("member", MEMBER_AGENT_URL, multitenant_agent, False)
    MEMBER_ADMIN = AgentType("member-admin", MEMBER_AGENT_URL, admin_agent, True)

    @staticmethod
    def from_str(role: str) -> Optional["Role"]:
        for item in Role:
            if item.role_name == role:
                return item

        return None

    @property
    def role_name(self) -> str:
        return self.value.name

    @property
    def agent_type(self) -> AgentType:
        return self.value
