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
    handle_tenant_update,
    onboard_tenant,
)
from app.dependencies import AcaPyAuth, Role, acapy_auth, agent_role
from app.error import CloudApiException
from app.facades.trust_registry import (
    Actor,
    actor_by_id,
    register_actor,
    remove_actor_by_id,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/tenants", tags=["admin: tenants"])

multitenant_admin = agent_role(Role.TENANT_ADMIN)


def tenant_api_key(role: Role, tenant_token: str):
    "Get the cloud api key for a tenant with specified role."

    if not role.agent_type.tenant_role:
        raise CloudApiException("Invalid role", 403)

    return f"{role.agent_type.tenant_role.name}.{tenant_token}"


@router.post("/", response_model=CreateTenantResponse)
async def create_tenant(
    body: CreateTenantRequest,
    aries_controller: AcaPyClient = Depends(multitenant_admin),
    auth: AcaPyAuth = Depends(acapy_auth),
) -> Tenant:
    """Create a new tenant."""
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
            wallet_name=uuid4().hex,
            wallet_type="askar",
        )
    )

    if body.roles and len(body.roles) > 0:
        onboard_result = await onboard_tenant(
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
    tenant_id: str, aries_controller: AcaPyClient = Depends(multitenant_admin)
):
    """Delete tenant by id."""
    wallet = await aries_controller.multitenancy.get_wallet(wallet_id=tenant_id)

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
    wallet = await aries_controller.multitenancy.get_wallet(wallet_id=tenant_id)

    response = await aries_controller.multitenancy.get_auth_token(
        wallet_id=wallet.wallet_id, body=CreateWalletTokenRequest()
    )

    return TenantAuth(access_token=tenant_api_key(auth.role, response.token))


@router.put("/{tenant_id}", response_model=Tenant)
async def update_tenant(
    tenant_id: str,
    body: UpdateTenantRequest,
    aries_controller: AcaPyClient = Depends(multitenant_admin),
) -> Tenant:
    """Update tenant by id."""
    wallet = await aries_controller.multitenancy.get_wallet(wallet_id=tenant_id)

    await handle_tenant_update(
        admin_controller=aries_controller, tenant_id=tenant_id, update=body
    )

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
) -> List[Tenant]:

    """Get tenants."""
    wallets = await aries_controller.multitenancy.get_wallets()

    if not wallets.results:
        return []

    # Only return wallet with current authentication role.
    return [
        tenant_from_wallet_record(wallet_record) for wallet_record in wallets.results
    ]


@router.get("/{tenant_id}", response_model=Tenant)
async def get_tenant(
    tenant_id: str, aries_controller: AcaPyClient = Depends(multitenant_admin)
) -> Tenant:
    """Get tenant by id."""
    wallet = await aries_controller.multitenancy.get_wallet(wallet_id=tenant_id)

    return tenant_from_wallet_record(wallet)
