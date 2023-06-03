import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import List, Optional, Union

import jwt
from aries_cloudcontroller import AcaPyClient
from fastapi import HTTPException
from fastapi.params import Depends
from fastapi.security import APIKeyHeader

from app.constants import ACAPY_MULTITENANT_JWT_SECRET
from app.role import Role

logger = logging.getLogger(__name__)


x_api_key_scheme = APIKeyHeader(name="x-api-key")


@dataclass
class AcaPyAuth:
    token: str
    role: Role
    wallet_id: str = None


@dataclass
class AcaPyAuthVerified(AcaPyAuth):
    wallet_id: str


def acapy_auth(auth: str = Depends(x_api_key_scheme)):
    if "." not in auth:
        raise HTTPException(401, "Unauthorized")

    try:
        [role_str, token] = auth.split(".", maxsplit=1)

        role = Role.from_str(role_str)
    except Exception:
        raise HTTPException(401, "Unauthorized")

    if not role:
        raise HTTPException(401, "Unauthorized")

    return AcaPyAuth(role=role, token=token)


def acapy_auth_verified(auth: AcaPyAuth = Depends(acapy_auth)):
    if auth.role.is_admin:
        if auth.token != auth.role.agent_type.x_api_key:
            raise HTTPException(403, "Unauthorized")

        wallet_id = "admin"
    else:
        try:
            # Decode JWT
            token_body = jwt.decode(
                auth.token, ACAPY_MULTITENANT_JWT_SECRET, algorithms=["HS256"]
            )
        except jwt.InvalidTokenError:
            raise HTTPException(403, "Unauthorized")

        wallet_id = token_body.get("wallet_id")

        if not wallet_id:
            raise HTTPException(403, "Unauthorized")

    return AcaPyAuthVerified(role=auth.role, token=auth.token, wallet_id=wallet_id)


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
async def get_governance_controller():
    # TODO: would be good to support this natively in AcaPyClient
    client = AcaPyClient(
        Role.GOVERNANCE.agent_type.base_url,
        api_key=Role.GOVERNANCE.agent_type.x_api_key,
    )

    yield client
    await client.close()


@asynccontextmanager
async def get_tenant_admin_controller():
    # TODO: would be good to support this natively in AcaPyClient
    client = AcaPyClient(
        Role.TENANT_ADMIN.agent_type.base_url,
        api_key=Role.TENANT_ADMIN.agent_type.x_api_key,
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
