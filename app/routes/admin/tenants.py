from secrets import token_urlsafe
from typing import List, Optional
from uuid import uuid4

import base58
from aries_cloudcontroller import (
    CreateWalletRequest,
    CreateWalletTokenRequest,
    UpdateWalletRequest,
    WalletRecord,
)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from uplink import Consumer, Query, get, returns

from app.dependencies.acapy_clients import get_tenant_admin_controller
from app.dependencies.auth import (
    AcaPyAuth,
    AcaPyAuthVerified,
    Role,
    acapy_auth,
    acapy_auth_tenant_admin,
)
from app.exceptions.cloud_api_error import CloudApiException
from app.models.tenants import (
    CreateTenantRequest,
    CreateTenantResponse,
    Tenant,
    TenantAuth,
    UpdateTenantRequest,
    tenant_from_wallet_record,
)
from app.services.onboarding import handle_tenant_update, onboard_tenant
from app.services.trust_registry import (
    Actor,
    TrustRegistryException,
    actor_by_id,
    assert_actor_name,
    register_actor,
    remove_actor_by_id,
)
from shared.log_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/tenants", tags=["admin: tenants"])


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


@router.post("", response_model=CreateTenantResponse)
async def create_tenant(
    body: CreateTenantRequest,
    auth: AcaPyAuth = Depends(acapy_auth),
) -> Tenant:
    """Create a new tenant."""
    bound_logger = logger.bind(body=body)
    bound_logger.info("POST request received: Starting tenant creation")

    name = body.name
    roles = body.roles

    try:
        actor_name_exists = await assert_actor_name(body.name)
    except TrustRegistryException:
        raise CloudApiException(
            "An error occurred when trying to register actor. Please try again"
        )

    if actor_name_exists:
        bound_logger.info("Actor exists can't create wallet")
        raise HTTPException(
            409, f"Can't create Tenant. Actor with name `{name}` already exists."
        )

    bound_logger.info("Actor name is unique, creating wallet")
    wallet_response = None
    async with get_tenant_admin_controller() as admin_controller:
        try:
            wallet_response = await admin_controller.multitenancy.create_wallet(
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
            bound_logger.debug("Wallet creation successful")

            if roles:
                bound_logger.info(
                    "Onboarding `{}` with requested roles: `{}`", name, roles
                )
                onboard_result = await onboard_tenant(
                    name=name,
                    roles=roles,
                    tenant_auth_token=wallet_response.token,
                    tenant_id=wallet_response.wallet_id,
                )
                bound_logger.debug("Registering actor in the trust registry")
                await register_actor(
                    actor=Actor(
                        id=wallet_response.wallet_id,
                        name=name,
                        roles=roles,
                        did=onboard_result.did,
                        didcomm_invitation=onboard_result.didcomm_invitation,
                    )
                )
        except HTTPException as http_error:
            bound_logger.error("Could not register actor: {}", http_error.detail)
            if wallet_response:
                bound_logger.info(
                    "Stray wallet was created for unregistered actor; deleting wallet"
                )
                await admin_controller.multitenancy.delete_wallet(
                    wallet_id=wallet_response.wallet_id
                )
                bound_logger.info("Wallet deleted.")
            raise
        except Exception:
            bound_logger.exception("An unhandled exception occurred")
            if wallet_response:
                bound_logger.info(
                    "Could not register actor, but wallet was created; deleting wallet"
                )
                await admin_controller.multitenancy.delete_wallet(
                    wallet_id=wallet_response.wallet_id
                )
                bound_logger.info("Wallet deleted.")
            raise

    response = CreateTenantResponse(
        tenant_id=wallet_response.wallet_id,
        created_at=wallet_response.created_at,
        image_url=body.image_url,
        updated_at=wallet_response.updated_at,
        tenant_name=name,
        access_token=tenant_api_key(auth.role, wallet_response.token),
        group_id=body.group_id,
    )
    bound_logger.debug("Successfully created tenant.")
    return response


@router.delete("/{tenant_id}")
async def delete_tenant_by_id(
    tenant_id: str,
    admin_auth: AcaPyAuthVerified = Depends(acapy_auth_tenant_admin),
):
    """Delete tenant by id."""
    bound_logger = logger.bind(body={"tenant_id": tenant_id})
    bound_logger.info("DELETE request received: Deleting tenant by id")

    async with get_tenant_admin_controller() as admin_controller:
        bound_logger.debug("Retrieving the wallet")
        wallet = await admin_controller.multitenancy.get_wallet(wallet_id=tenant_id)
        if not wallet:
            bound_logger.error("Bad request: Wallet not found.")
            raise HTTPException(404, f"Wallet for tenant id `{tenant_id}` not found.")

        # wallet_id is the id of the actor in the trust registry.
        # This makes it a lot easier to link a tenant to an actor
        # in the trust registry, especially if the tenant does not have
        # a public did.
        bound_logger.debug("Retrieving tenant from trust registry")
        actor = await actor_by_id(wallet.wallet_id)

        # Remove actor if found
        if actor:
            bound_logger.debug("Actor found, removing from trust registry")
            await remove_actor_by_id(wallet.wallet_id)

        bound_logger.debug("Deleting wallet")
        await admin_controller.multitenancy.delete_wallet(wallet_id=tenant_id)
        bound_logger.info("Successfully deleted tenant.")


@router.get("/{tenant_id}/access-token", response_model=TenantAuth)
async def get_tenant_auth_token(
    tenant_id: str,
    auth: AcaPyAuth = Depends(acapy_auth),
):
    bound_logger = logger.bind(body={"tenant_id": tenant_id})
    bound_logger.info("GET request received: Access token for tenant")

    async with get_tenant_admin_controller() as admin_controller:
        bound_logger.debug("Retrieving the wallet")
        wallet = await admin_controller.multitenancy.get_wallet(wallet_id=tenant_id)
        if not wallet:
            bound_logger.error("Bad request: Wallet not found.")
            raise HTTPException(404, f"Wallet for tenant id `{tenant_id}` not found.")

        bound_logger.debug("Getting auth token for wallet")
        response = await admin_controller.multitenancy.get_auth_token(
            wallet_id=wallet.wallet_id, body=CreateWalletTokenRequest()
        )

    response = TenantAuth(access_token=tenant_api_key(auth.role, response.token))
    bound_logger.info("Successfully retrieved access token.")
    return response


@router.put("/{tenant_id}", response_model=Tenant)
async def update_tenant(
    tenant_id: str,
    body: UpdateTenantRequest,
    admin_auth: AcaPyAuthVerified = Depends(acapy_auth_tenant_admin),
) -> Tenant:
    """Update tenant by id."""
    bound_logger = logger.bind(body={"tenant_id": tenant_id, "body": body})
    bound_logger.info("PUT request received: Update tenant")

    async with get_tenant_admin_controller() as admin_controller:
        await handle_tenant_update(
            admin_controller=admin_controller, tenant_id=tenant_id, update=body
        )

        bound_logger.debug("Updating wallet")
        wallet = await admin_controller.multitenancy.update_wallet(
            wallet_id=tenant_id,
            body=UpdateWalletRequest(
                image_url=body.image_url,
                label=body.name,
            ),
        )

    response = tenant_from_wallet_record(wallet)
    bound_logger.info("Successfully updated tenant.")
    return response


@router.get("/{tenant_id}", response_model=Tenant)
async def get_tenant(
    tenant_id: str,
    admin_auth: AcaPyAuthVerified = Depends(acapy_auth_tenant_admin),
) -> Tenant:
    """Get tenant by id."""
    bound_logger = logger.bind(body={"wallet_id": tenant_id})
    bound_logger.info("GET request received: Fetch tenant by id")

    async with get_tenant_admin_controller() as admin_controller:
        bound_logger.debug("Retrieving the wallet")
        wallet = await admin_controller.multitenancy.get_wallet(wallet_id=tenant_id)
        if not wallet:
            bound_logger.error("Bad request: Wallet not found.")
            raise HTTPException(404, f"Wallet for tenant id `{tenant_id}` not found.")

    response = tenant_from_wallet_record(wallet)
    bound_logger.info("Successfully fetched tenant from wallet record.")
    return response


@router.get("", response_model=List[Tenant])
async def get_tenants(
    group_id: str = None,
    admin_auth: AcaPyAuthVerified = Depends(acapy_auth_tenant_admin),
) -> List[Tenant]:
    """Get tenants (by group id.)"""
    bound_logger = logger.bind(body={"group_id": group_id})
    bound_logger.info("GET request received: Fetch tenants by group id")

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

    async with get_tenant_admin_controller() as admin_controller:
        admin_controller.multitenancy = MultitenancyApi(
            base_url=admin_controller.base_url, client=admin_controller.client
        )
        if not group_id:
            bound_logger.info("No group id specified; fetching all wallets")
            wallets = await admin_controller.multitenancy.get_wallets()

            if not wallets.results:
                bound_logger.info("No wallets found.")
                return []

            # Only return wallet with current authentication role.
            response = [
                tenant_from_wallet_record(wallet_record)
                for wallet_record in wallets.results
            ]
            bound_logger.info("Successfully fetched wallets.")
            return response

        bound_logger.info("Fetching wallets by group id")
        wallets = await admin_controller.multitenancy.get_wallets(group_id=group_id)

    if not wallets.results:
        bound_logger.info("No wallets found for requested group id.")
        return []

    response = [
        tenant_from_wallet_record(wallet_record) for wallet_record in wallets.results
    ]
    bound_logger.info("Successfully fetched wallets by group id.")
    return response
