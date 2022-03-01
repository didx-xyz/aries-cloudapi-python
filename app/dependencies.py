import logging
from contextlib import asynccontextmanager
from typing import List, Optional, Union

from aries_cloudcontroller import AcaPyClient
from fastapi import HTTPException
from fastapi.params import Depends
from fastapi.security import APIKeyHeader

from app.role import Role

logger = logging.getLogger(__name__)


x_api_key_scheme = APIKeyHeader(name="x-api-key")


class AcaPyAuth:
    token: str
    role: Role

    def __init__(self, *, role: "Role", token: str) -> None:
        self.role = role
        self.token = token


def acapy_auth(auth: str = Depends(x_api_key_scheme)):
    if not "." in auth:
        raise HTTPException(401, "Unauthorized")

    [role_str, token] = auth.split(".", maxsplit=1)

    role = Role.from_str(role_str)

    if not role:
        raise HTTPException(401, "Unauthorized")

    return AcaPyAuth(role=role, token=token)


async def admin_agent_selector(auth: AcaPyAuth = Depends(acapy_auth)):
    if not auth.role.is_admin:
        raise HTTPException(403, "Unauthorized")

    async with asynccontextmanager(agent_selector)(auth) as x:
        yield x


def agent_role(role: Union["Role", List["Role"]]):
    async def run(auth: AcaPyAuth = Depends(acapy_auth)):
        roles = role if isinstance(role, List) else [role]

        if auth.role not in roles:
            raise HTTPException(403, "Unauthorized")

        async with asynccontextmanager(agent_selector)(auth) as x:
            yield x

    return run


@asynccontextmanager
async def get_yoma_controller():
    # TODO: would be good to support this natively in AcaPyClient
    client = AcaPyClient(
        Role.YOMA.agent_type.base_url, api_key=Role.YOMA.agent_type.x_api_key
    )

    yield client
    await client.close()


@asynccontextmanager
async def get_tenant_controller(role: "Role", auth_token: str):
    client = AcaPyClient(
        role.agent_type.base_url,
        api_key=role.agent_type.x_api_key,
        tenant_jwt=auth_token,
    )

    yield client
    await client.close()


async def agent_selector(auth: AcaPyAuth = Depends(acapy_auth)):
    if not auth.token or auth.token == "":
        raise HTTPException(403, "Missing authorization key")

    tenant_jwt: Optional[str] = None
    x_api_key: Optional[str] = None

    # Tenant of multitenant agent
    if auth.role.is_multitenant and not auth.role.is_admin:
        tenant_jwt = auth.token
        x_api_key = auth.role.agent_type.x_api_key
    else:
        x_api_key = auth.token

    agent = None
    try:
        # yield the controller
        agent = AcaPyClient(
            base_url=auth.role.agent_type.base_url,
            api_key=x_api_key,
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
