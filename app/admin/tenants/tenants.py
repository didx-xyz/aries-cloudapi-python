import logging
from secrets import token_urlsafe
from typing import List
from uuid import uuid4

from aries_cloudcontroller import (
    AcaPyClient,
    CreateWalletRequest,
    CreateWalletTokenRequest,
    RemoveWalletRequest,
    UpdateWalletRequest,
)
from aries_cloudcontroller.model.wallet_record import WalletRecord
from fastapi import APIRouter, Depends

from app.admin.tenants.models import (
    CreateTenantRequest,
    CreateTenantResponse,
    Tenant,
    TenantAuth,
    UpdateTenantRequest,
    tenant_from_wallet_record,
)
from app.admin.tenants.onboarding import (
    handle_ecosystem_tenant_update,
    onboard_ecosystem_tenant,
)
from app.dependencies import AcaPyAuth, Role, acapy_auth, agent_role
from app.error import CloudApiException
from app.facades.trust_registry import (
    Actor,
    actor_by_id,
    register_actor,
    remove_actor_by_id,
)
from app.role import AgentType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/tenants", tags=["admin: tenants"])

multitenant_admin = agent_role([Role.MEMBER_ADMIN, Role.ECOSYSTEM_ADMIN])


def tenant_api_key(role: Role, tenant_token: str):
    "Get the cloud api key for a tenant with specified role."

    if not role.agent_type.tenant_role:
        raise CloudApiException("Invalid role", 403)

    return f"{role.agent_type.tenant_role.name}.{tenant_token}"


async def get_tenant_for_admin_role(
    aries_controller: AcaPyClient, tenant_id: str, role: Role
) -> WalletRecord:
    """Get the wallet record for a tenant with specified id.

    Will throw an error if the wallet is not created with same role as
    role specified in method parameters. This is identified by a role prefix
    to the wallet name. E.g. wallet name "member.xxxxxxxxxxxxxxxx" means
    the wallet was created in the context of a member.

    Args:
        aries_controller (AcaPyClient): aries controller to use
        tenant_id (str): Tenant id to retrieve the wallet for
        role (Role): Role the wallet should be in

    Raises:
        CloudApiException: When the role of the wallet does not match the
            role from the method parameteres

    Returns:
        WalletRecord: The wallet record.
    """

    # We retrieve the wallet to make sure it exists
    wallet = await aries_controller.multitenancy.get_wallet(wallet_id=tenant_id)

    # This checks if the role of the wallet is in the current context. It would be possible
    # to retrieve a member wallet while authorized as an ecosystem admin.
    if not wallet_is_for_admin_role(wallet, role):
        raise CloudApiException(f"Unauthorized", 401)

    return wallet


def wallet_is_for_admin_role(wallet: WalletRecord, role: Role):
    wallet_name: str = wallet.settings.get("wallet.name")

    tenant_agent_type = role.agent_type.tenant_role

    return wallet_name.startswith(f"{tenant_agent_type.name}.")


def get_wallet_name_for_role(agent_type: AgentType) -> str:
    return f"{agent_type.name}.{uuid4().hex}"


@router.post("/", response_model=CreateTenantResponse)
async def create_tenant(
    body: CreateTenantRequest,
    aries_controller: AcaPyClient = Depends(multitenant_admin),
    auth: AcaPyAuth = Depends(acapy_auth),
) -> Tenant:
    """Create a new tenant."""
    if auth.role == Role.MEMBER_ADMIN and body.roles and len(body.roles) > 0:
        raise CloudApiException(
            "Not allowed to provide roles for member tenants, only ecosystem tenants",
            403,
        )

    tenant_role = auth.role.agent_type.tenant_role

    if not tenant_role:
        raise CloudApiException(
            f"Unable to create tenant for agent type ${auth.role}, as it has no admin rights over tenants"
        )

    wallet_response = await aries_controller.multitenancy.create_wallet(
        body=CreateWalletRequest(
            image_url=body.image_url,
            key_management_mode="managed",
            label=body.name,
            wallet_key=token_urlsafe(48),
            wallet_name=get_wallet_name_for_role(tenant_role),
            wallet_type="askar",
        )
    )

    if auth.role == Role.ECOSYSTEM_ADMIN and body.roles and len(body.roles) > 0:
        onboard_result = await onboard_ecosystem_tenant(
            name=body.name,
            roles=body.roles,
            tenant_auth_token=wallet_response.token,
            tenant_id=wallet_response.wallet_id,
        )

        await register_actor(
            actor=Actor(
                id=wallet_response.wallet_id,
                name=body.name,
                roles=list(body.roles),
                did=onboard_result.did,
                didcomm_invitation=onboard_result.didcomm_invitation,
            )
        )

    return CreateTenantResponse(
        tenant_id=wallet_response.wallet_id,
        created_at=wallet_response.created_at,
        image_url=body.image_url,
        updated_at=wallet_response.updated_at,
        tenant_name=body.name,
        access_token=tenant_api_key(auth.role, wallet_response.token),
    )


@router.delete("/{tenant_id}")
async def delete_tenant_by_id(
    tenant_id: str,
    aries_controller: AcaPyClient = Depends(multitenant_admin),
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """Delete tenant by id."""
    wallet = await get_tenant_for_admin_role(
        aries_controller=aries_controller,
        tenant_id=tenant_id,
        role=auth.role,
    )

    # wallet_id is the id of the actor in the trust registry.
    # This makes it a lot easier to link a tenant to an actor
    # in the trust registry, especially if the tenant does not have
    # a public did.
    actor = await actor_by_id(wallet.wallet_id)

    # Remove actor if found
    if actor:
        await remove_actor_by_id(wallet.wallet_id)

    await aries_controller.multitenancy.delete_wallet(
        wallet_id=tenant_id, body=RemoveWalletRequest()
    )


@router.get("/{tenant_id}/access-token", response_model=TenantAuth)
async def get_tenant_auth_token(
    tenant_id: str,
    aries_controller: AcaPyClient = Depends(multitenant_admin),
    auth: AcaPyAuth = Depends(acapy_auth),
):
    wallet = await get_tenant_for_admin_role(
        aries_controller=aries_controller, tenant_id=tenant_id, role=auth.role
    )

    response = await aries_controller.multitenancy.get_auth_token(
        wallet_id=wallet.wallet_id, body=CreateWalletTokenRequest()
    )

    return TenantAuth(access_token=tenant_api_key(auth.role, response.token))


@router.put("/{tenant_id}", response_model=Tenant)
async def update_tenant(
    tenant_id: str,
    body: UpdateTenantRequest,
    aries_controller: AcaPyClient = Depends(multitenant_admin),
    auth: AcaPyAuth = Depends(acapy_auth),
) -> Tenant:
    """Update tenant by id."""
    wallet = await get_tenant_for_admin_role(
        aries_controller=aries_controller, tenant_id=tenant_id, role=auth.role
    )

    # Only when in ecosystem context we update the trust registry / ecosystem onboarding steps
    if auth.role == Role.ECOSYSTEM_ADMIN:
        await handle_ecosystem_tenant_update(
            admin_controller=aries_controller, tenant_id=tenant_id, update=body
        )

    elif auth.role == Role.MEMBER_ADMIN and body.roles and len(body.roles) > 0:
        raise CloudApiException("Roles not allowed for member", 403)

    wallet = await aries_controller.multitenancy.update_wallet(
        wallet_id=tenant_id,
        body=UpdateWalletRequest(
            image_url=body.image_url,
            label=body.name,
        ),
    )

    return tenant_from_wallet_record(wallet)


@router.get("/", response_model=List[Tenant])
async def get_tenants(
    aries_controller: AcaPyClient = Depends(multitenant_admin),
    auth: AcaPyAuth = Depends(acapy_auth),
) -> List[Tenant]:

    """Get tenants."""
    wallets = await aries_controller.multitenancy.get_wallets()

    if not wallets.results:
        return []

    # Only return wallet with current authentication role.
    return [
        tenant_from_wallet_record(wallet_record)
        for wallet_record in wallets.results
        if wallet_is_for_admin_role(wallet_record, auth.role)
    ]


@router.get("/{tenant_id}", response_model=Tenant)
async def get_tenant(
    tenant_id: str,
    aries_controller: AcaPyClient = Depends(multitenant_admin),
    auth: AcaPyAuth = Depends(acapy_auth),
) -> Tenant:
    """Get tenant by id."""
    wallet = await get_tenant_for_admin_role(
        aries_controller=aries_controller, tenant_id=tenant_id, role=auth.role
    )

    return tenant_from_wallet_record(wallet)
