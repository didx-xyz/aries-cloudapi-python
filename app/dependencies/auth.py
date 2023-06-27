import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Union

import jwt
from aries_cloudcontroller import AcaPyClient
from aries_cloudcontroller.util.acapy_client_session import AcaPyClientSession
from fastapi import HTTPException
from fastapi.params import Depends
from fastapi.security import APIKeyHeader

from app.dependencies.role import Role
from shared import ACAPY_MULTITENANT_JWT_SECRET

logger = logging.getLogger(__name__)


x_api_key_scheme = APIKeyHeader(name="x-api-key")


@dataclass
class AcaPyAuth:
    token: str
    role: Role


@dataclass
class AcaPyAuthVerified(AcaPyAuth):
    wallet_id: str


def acapy_auth(auth: str = Depends(x_api_key_scheme)) -> AcaPyAuth:
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


def acapy_auth_verified(auth: AcaPyAuth = Depends(acapy_auth)) -> AcaPyAuthVerified:
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


def acapy_auth_governance(auth: AcaPyAuth = Depends(acapy_auth)) -> AcaPyAuthVerified:
    if auth.role == Role.GOVERNANCE:
        return AcaPyAuthVerified(role=auth.role, token=auth.token, wallet_id="admin")
    else:
        raise HTTPException(403, "Unauthorized")


def acapy_auth_tenant_admin(auth: AcaPyAuth = Depends(acapy_auth)) -> AcaPyAuthVerified:
    if auth.role == Role.TENANT_ADMIN:
        return AcaPyAuthVerified(role=auth.role, token=auth.token, wallet_id="admin")
    else:
        raise HTTPException(403, "Unauthorized")


@asynccontextmanager
async def get_governance_controller():
    # TODO: would be good to support this natively in AcaPyClient
    async with AcaPyClientSession(
        api_key=Role.GOVERNANCE.agent_type.x_api_key
    ) as session:
        async with AcaPyClient(
            Role.GOVERNANCE.agent_type.base_url, client_session=session
        ) as client:
            yield client


@asynccontextmanager
async def get_tenant_admin_controller():
    # TODO: would be good to support this natively in AcaPyClient
    async with AcaPyClientSession(
        api_key=Role.TENANT_ADMIN.agent_type.x_api_key
    ) as session:
        async with AcaPyClient(
            Role.TENANT_ADMIN.agent_type.base_url, client_session=session
        ) as client:
            yield client


@asynccontextmanager
async def get_tenant_controller(role: Role, auth_token: str):
    async with AcaPyClientSession(
        api_key=role.agent_type.x_api_key, tenant_jwt=auth_token
    ) as session:
        async with AcaPyClient(
            role.agent_type.base_url, client_session=session
        ) as client:
            yield client


def client_from_auth(auth: Union[AcaPyAuth, AcaPyAuthVerified]) -> AcaPyClient:
    if not auth or not auth.token:
        raise HTTPException(403, "Missing authorization key")

    tenant_jwt = None

    if auth.role.is_multitenant and not auth.role.is_admin:
        tenant_jwt = auth.token
        x_api_key = auth.role.agent_type.x_api_key
    else:
        x_api_key = auth.token

    client = AcaPyClient(
        base_url=auth.role.agent_type.base_url,
        api_key=x_api_key,
        tenant_jwt=tenant_jwt,
    )
    return client
