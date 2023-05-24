import logging
from secrets import token_urlsafe
from typing import List, Optional
from uuid import uuid4
import httpx
from http import HTTPStatus

import base58
from aries_cloudcontroller import (
    AcaPyClient,
    CreateWalletRequest,
    CreateWalletTokenRequest,
    RemoveWalletRequest,
    UpdateWalletRequest,
    WalletRecord,
)
from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from uplink import Consumer, Query, get, returns

from app.admin.tenants.models import (
    CreateTenantRequest,
    CreateTenantResponse,
    Tenant,
    TenantAuth,
    UpdateTenantRequest,
    tenant_from_wallet_record,
)
from app.admin.tenants.onboarding import handle_tenant_update, onboard_tenant
from app.facades.trust_registry import (
    Actor,
    actor_by_id,
    register_actor,
    remove_actor_by_id,
    actor_by_name,
)
from shared import CloudApiException
from shared.dependencies.auth import AcaPyAuth, Role, acapy_auth, agent_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/tenants", tags=["admin: tenants"])

multitenant_admin = agent_role(Role.TENANT_ADMIN)


class CreateWalletRequestWithGroups(CreateWalletRequest):
    group_id: Optional[str] = None


class WalletRecordWithGroups(WalletRecord):
    group_id: Optional[str] = None


class WalletListWithGroups(BaseModel):
    results: Optional[List[WalletRecordWithGroups]] = None


def tenant_api_key(role: Role, tenant_token: str):
    "Get the cloud api key for a tenant with specified role."

    if not role.agent_type.tenant_role:
        raise CloudApiException("Invalid role", 403)

    return f"{role.agent_type.tenant_role.name}.{tenant_token}"

# async def send_webhook_event(url: str, data: dict):
#     async with httpx.AsyncClient() as client:
#         response = await client.post(url, json=data)
#         if response.status_code != HTTPStatus.OK:
#             logger.error("Failed to send webhook event. Status code: %s, message: %s",
#                          response.status_code, response.text)
async def onboard_and_register_tenant(
    name: str,
    roles: List[str],
    tenant_auth_token: str,
    tenant_id: str,
    # webhook_url: str,  # this is the URL where we'll send the webhook events
    # background_tasks: BackgroundTasks,
):
    onboard_result = await onboard_tenant(
        name=name,
        roles=roles,
        tenant_auth_token=tenant_auth_token,
        tenant_id=tenant_id,
    )

    # Send a webhook event
    # background_tasks.add_task(
    #     send_webhook_event,
    #     webhook_url,
    #     {"status": "tenant_onboarded", "tenant_id": tenant_id},
    # )

    await register_actor(
        actor=Actor(
            id=tenant_id,
            name=name,
            roles=list(roles),
            did=onboard_result.did,
            didcomm_invitation=onboard_result.didcomm_invitation,
        )
    )

    # Send another webhook event
    # background_tasks.add_task(
    #     send_webhook_event,
    #     webhook_url,
    #     {"status": "actor_registered", "tenant_id": tenant_id},
    # )

@router.post("", response_model=CreateTenantResponse)
async def create_tenant(
    body: CreateTenantRequest,
    aries_controller: AcaPyClient = Depends(multitenant_admin),
    auth: AcaPyAuth = Depends(acapy_auth),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> Tenant:
    """Create a new tenant."""
    tenant_role = auth.role.agent_type.tenant_role

    if not tenant_role:
        raise CloudApiException(
            f"Unable to create tenant for agent type ${auth.role}, as it has no admin rights over tenants"
        )

    # check if actor with duplicate name exist
    actor = await actor_by_name(body.name)
    print("actor", actor)
    # actor with same name exist in registry, throw exception
    if actor and body.roles and len(body.roles) > 0:
        raise CloudApiException(
            f"Tenant with name: '{body.name}' already exist in Trust Registry. Please choose a different name"
        )

    wallet_response = await aries_controller.multitenancy.create_wallet(
        body=CreateWalletRequestWithGroups(
            image_url=body.image_url,
            key_management_mode="managed",
            label=body.name,
            wallet_key=base58.b58encode(token_urlsafe(48)),
            wallet_name=uuid4().hex,
            wallet_type="askar",
            group_id=body.group_id,
        )
    )

    if body.roles and len(body.roles) > 0:
        background_tasks.add_task(
            onboard_and_register_tenant,
            name=body.name,
            roles=body.roles,
            tenant_auth_token=wallet_response.token,
            tenant_id=wallet_response.wallet_id,
        )

    return CreateTenantResponse(
        tenant_id=wallet_response.wallet_id,
        created_at=wallet_response.created_at,
        image_url=body.image_url,
        updated_at=wallet_response.updated_at,
        tenant_name=body.name,
        access_token=tenant_api_key(auth.role, wallet_response.token),
        group_id=body.group_id,
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


@router.get("/{tenant_id}", response_model=Tenant)
async def get_tenant(
    tenant_id: str, aries_controller: AcaPyClient = Depends(multitenant_admin)
) -> Tenant:
    """Get tenant by id."""
    wallet = await aries_controller.multitenancy.get_wallet(wallet_id=tenant_id)

    return tenant_from_wallet_record(wallet)


@router.get("", response_model=List[Tenant])
async def get_tenants(
    group_id: str = None, aries_controller: AcaPyClient = Depends(multitenant_admin)
) -> List[Tenant]:
    """Get tenants (by group id.)"""

    # NOTE: Since this is using the groups plugin we need to override the
    # controller to be aware of this
    class MultitenancyApi(Consumer):
        async def get_wallets(
            self, *, group_id: Optional[str] = None, wallet_name: Optional[str] = None
        ) -> WalletListWithGroups:
            """Query subwallets"""
            return await self.__get_wallets(
                group_id=group_id,
                wallet_name=wallet_name,
            )

        @returns.json
        @get("/multitenancy/wallets")
        def __get_wallets(
            self, *, group_id: Query = None, wallet_name: Query = None
        ) -> WalletListWithGroups:
            """Internal uplink method for get_wallets"""

    aries_controller.multitenancy = MultitenancyApi(
        base_url=aries_controller.base_url, client=aries_controller.client
    )
    if not group_id:
        wallets = await aries_controller.multitenancy.get_wallets()

        if not wallets.results:
            return []

        # Only return wallet with current authentication role.
        return [
            tenant_from_wallet_record(wallet_record)
            for wallet_record in wallets.results
        ]

    wallets = await aries_controller.multitenancy.get_wallets(group_id=group_id)

    if not wallets.results or len(wallets.results) == 0:
        return []

    return [
        tenant_from_wallet_record(wallet_record) for wallet_record in wallets.results
    ]
