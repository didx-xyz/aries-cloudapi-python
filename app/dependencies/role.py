from enum import Enum
from typing import NamedTuple, Optional, Union

from aries_cloudcontroller import AcaPyClient
from fastapi import HTTPException

from app.dependencies.auth import AcaPyAuth, AcaPyAuthVerified
from shared.constants import (
    GOVERNANCE_AGENT_API_KEY,
    GOVERNANCE_AGENT_URL,
    TENANT_AGENT_API_KEY,
    TENANT_AGENT_URL,
)


class AgentType(NamedTuple):
    name: str
    base_url: str
    is_multitenant: bool
    tenant_role: Optional["AgentType"]
    is_admin: bool
    x_api_key: Optional[str]


GOVERNANCE_AGENT_TYPE = AgentType(
    name="governance",
    base_url=GOVERNANCE_AGENT_URL,
    is_multitenant=False,
    tenant_role=None,
    is_admin=True,
    x_api_key=GOVERNANCE_AGENT_API_KEY,
)

TENANT_AGENT_TYPE = AgentType(
    name="tenant",
    base_url=TENANT_AGENT_URL,
    is_multitenant=True,
    tenant_role=None,
    is_admin=False,
    x_api_key=TENANT_AGENT_API_KEY,
)

TENANT_ADMIN_AGENT_TYPE = AgentType(
    name="tenant-admin",
    base_url=TENANT_AGENT_URL,
    is_multitenant=True,
    tenant_role=TENANT_AGENT_TYPE,
    is_admin=True,
    x_api_key=TENANT_AGENT_API_KEY,
)


class Role(Enum):
    GOVERNANCE = GOVERNANCE_AGENT_TYPE
    TENANT = TENANT_AGENT_TYPE
    TENANT_ADMIN = TENANT_ADMIN_AGENT_TYPE

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

    @property
    def is_admin(self) -> bool:
        return self.value.is_admin

    @property
    def is_multitenant(self) -> bool:
        return self.value.is_multitenant


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
