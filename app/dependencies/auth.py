from dataclasses import dataclass

import jwt
from fastapi import HTTPException
from fastapi.params import Depends
from fastapi.security import APIKeyHeader

from app.dependencies.role import Role
from shared import ACAPY_MULTITENANT_JWT_SECRET

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
