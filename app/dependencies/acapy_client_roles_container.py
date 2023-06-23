from aries_cloudcontroller import AcaPyClient
from dependency_injector import containers, providers

from app.dependencies.role import Role


class AcaPyClientContainer(containers.DeclarativeContainer):
    governance_client = providers.Singleton(
        AcaPyClient,
        base_url=Role.GOVERNANCE.agent_type.base_url,
        api_key=Role.GOVERNANCE.agent_type.x_api_key,
    )
    tenant_admin_client = providers.Singleton(
        AcaPyClient,
        base_url=Role.TENANT_ADMIN.agent_type.base_url,
        api_key=Role.TENANT_ADMIN.agent_type.x_api_key,
    )
    tenant_client = providers.Singleton(
        AcaPyClient,
        base_url=Role.TENANT.agent_type.base_url,
        api_key=Role.TENANT.agent_type.x_api_key,
    )


container = AcaPyClientContainer()
