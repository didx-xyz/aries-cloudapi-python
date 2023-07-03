from typing import Union

from aries_cloudcontroller import AcaPyClient
from fastapi import HTTPException

from app.dependencies.auth import AcaPyAuth, AcaPyAuthVerified
from app.dependencies.role import Role


def get_governance_controller() -> AcaPyClient:
    return AcaPyClient(
        base_url=Role.GOVERNANCE.agent_type.base_url,
        api_key=Role.GOVERNANCE.agent_type.x_api_key,
    )


def get_tenant_admin_controller() -> AcaPyClient:
    return AcaPyClient(
        base_url=Role.TENANT_ADMIN.agent_type.base_url,
        api_key=Role.TENANT_ADMIN.agent_type.x_api_key,
    )


def get_tenant_controller(auth_token: str) -> AcaPyClient:
    return AcaPyClient(
        base_url=Role.TENANT.agent_type.base_url,
        api_key=Role.TENANT.agent_type.x_api_key,
        tenant_jwt=auth_token,
    )


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
