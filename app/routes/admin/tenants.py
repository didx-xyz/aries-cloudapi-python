from secrets import token_urlsafe
from typing import List, Optional
from uuid import uuid4

import base58
from aries_cloudcontroller import CreateWalletTokenRequest, UpdateWalletRequest
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies.acapy_clients import get_tenant_admin_controller
from app.dependencies.auth import (
    AcaPyAuth,
    AcaPyAuthVerified,
    acapy_auth,
    acapy_auth_tenant_admin,
    tenant_api_key,
)
from app.exceptions.cloud_api_error import CloudApiException
from app.exceptions.trust_registry_exception import TrustRegistryException
from app.models.tenants import (
    CreateTenantRequest,
    CreateTenantResponse,
    CreateWalletRequestWithGroups,
    Tenant,
    TenantAuth,
    UpdateTenantRequest,
)
from app.models.trust_registry import Actor
from app.services.onboarding.tenants import handle_tenant_update, onboard_tenant
from app.services.trust_registry.actors import (
    fetch_actor_by_id,
    register_actor,
    remove_actor_by_id,
)
from app.services.trust_registry.util.actor import assert_actor_name
from app.util.tenants import tenant_from_wallet_record
from shared.log_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/tenants", tags=["admin: tenants"])


@router.post("", response_model=CreateTenantResponse)
async def create_tenant(
    body: CreateTenantRequest,
    auth: AcaPyAuth = Depends(acapy_auth),
) -> CreateTenantResponse:
    """Create a new tenant."""
    bound_logger = logger.bind(body=body)
    bound_logger.info("POST request received: Starting tenant creation")

    name = body.name
    roles = body.roles
    wallet_name=body.wallet_name or uuid4().hex,

    if roles:
        bound_logger.info("Create tenant with roles. Assert name is unique")
        try:
            actor_name_exists = await assert_actor_name(name)
        except TrustRegistryException:
            raise CloudApiException(
                "An error occurred when trying to register actor. Please try again"
            )

        if actor_name_exists:
            bound_logger.info("Actor name already exists; can't create wallet")
            raise HTTPException(
                409, f"Can't create Tenant. Actor with name `{name}` already exists."
            )
        bound_logger.info("Actor name is unique")

    wallet_response = None
    async with get_tenant_admin_controller() as admin_controller:
        try:
            bound_logger.info("Creating wallet")
            wallet_response = await admin_controller.multitenancy.create_wallet(
                body=CreateWalletRequestWithGroups(
                    image_url=body.image_url,
                    key_management_mode="managed",
                    label=name,
                    wallet_key=base58.b58encode(token_urlsafe(48)).decode(),
                    wallet_name=wallet_name,
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
                    wallet_auth_token=wallet_response.token,
                    wallet_id=wallet_response.wallet_id,
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
        wallet_id=wallet_response.wallet_id,
        tenant_name=name,
        wallet_name=wallet_name,
        created_at=wallet_response.created_at,
        image_url=body.image_url,
        updated_at=wallet_response.updated_at,
        access_token=tenant_api_key(auth.role, wallet_response.token),
        group_id=body.group_id,
    )
    bound_logger.debug("Successfully created tenant.")
    return response


@router.delete("/{wallet_id}")
async def delete_tenant_by_id(
    wallet_id: str,
    admin_auth: AcaPyAuthVerified = Depends(acapy_auth_tenant_admin),
):
    """Delete tenant by id."""
    bound_logger = logger.bind(body={"wallet_id": wallet_id})
    bound_logger.info("DELETE request received: Deleting tenant by id")

    async with get_tenant_admin_controller() as admin_controller:
        bound_logger.debug("Retrieving the wallet")
        wallet = await admin_controller.multitenancy.get_wallet(wallet_id=wallet_id)
        if not wallet:
            bound_logger.error("Bad request: Wallet not found.")
            raise HTTPException(404, f"Wallet with id `{wallet_id}` not found.")

        # wallet_id is the id of the actor in the trust registry.
        # This makes it a lot easier to link a tenant to an actor
        # in the trust registry, especially if the tenant does not have
        # a public did.
        bound_logger.debug("Retrieving tenant from trust registry")
        actor = await fetch_actor_by_id(wallet.wallet_id)

        # Remove actor if found
        if actor:
            bound_logger.debug("Actor found, removing from trust registry")
            await remove_actor_by_id(wallet.wallet_id)

        bound_logger.debug("Deleting wallet")
        await admin_controller.multitenancy.delete_wallet(wallet_id=wallet_id)
        bound_logger.info("Successfully deleted tenant.")


@router.get("/{wallet_id}/access-token", response_model=TenantAuth)
async def get_wallet_auth_token(
    wallet_id: str,
    auth: AcaPyAuth = Depends(acapy_auth),
) -> TenantAuth:
    bound_logger = logger.bind(body={"wallet_id": wallet_id})
    bound_logger.info("GET request received: Access token for tenant")

    async with get_tenant_admin_controller() as admin_controller:
        bound_logger.debug("Retrieving the wallet")
        wallet = await admin_controller.multitenancy.get_wallet(wallet_id=wallet_id)
        if not wallet:
            bound_logger.error("Bad request: Wallet not found.")
            raise HTTPException(404, f"Wallet with id `{wallet_id}` not found.")

        bound_logger.debug("Getting auth token for wallet")
        response = await admin_controller.multitenancy.get_auth_token(
            wallet_id=wallet.wallet_id, body=CreateWalletTokenRequest()
        )

    response = TenantAuth(access_token=tenant_api_key(auth.role, response.token))
    bound_logger.info("Successfully retrieved access token.")
    return response


@router.put("/{wallet_id}", response_model=Tenant)
async def update_tenant(
    wallet_id: str,
    body: UpdateTenantRequest,
    admin_auth: AcaPyAuthVerified = Depends(acapy_auth_tenant_admin),
) -> Tenant:
    """Update tenant by id."""
    bound_logger = logger.bind(body={"wallet_id": wallet_id, "body": body})
    bound_logger.info("PUT request received: Update tenant")

    async with get_tenant_admin_controller() as admin_controller:
        await handle_tenant_update(
            admin_controller=admin_controller, wallet_id=wallet_id, update=body
        )

        bound_logger.debug("Updating wallet")
        wallet = await admin_controller.multitenancy.update_wallet(
            wallet_id=wallet_id,
            body=UpdateWalletRequest(
                image_url=body.image_url,
                label=body.name,
            ),
        )

    response = tenant_from_wallet_record(wallet)
    bound_logger.info("Successfully updated tenant.")
    return response


@router.get("/{wallet_id}", response_model=Tenant)
async def get_tenant(
    wallet_id: str,
    admin_auth: AcaPyAuthVerified = Depends(acapy_auth_tenant_admin),
) -> Tenant:
    """Get tenant by id."""
    bound_logger = logger.bind(body={"wallet_id": wallet_id})
    bound_logger.info("GET request received: Fetch tenant by id")

    async with get_tenant_admin_controller() as admin_controller:
        bound_logger.debug("Retrieving the wallet")
        wallet = await admin_controller.multitenancy.get_wallet(wallet_id=wallet_id)
        if not wallet:
            bound_logger.error("Bad request: Wallet not found.")
            raise HTTPException(404, f"Wallet with id `{wallet_id}` not found.")

    response = tenant_from_wallet_record(wallet)
    bound_logger.info("Successfully fetched tenant from wallet record.")
    return response


@router.get("", response_model=List[Tenant])
async def get_tenants(
    wallet_name: Optional[str] = None,
    group_id: Optional[str] = None,
    admin_auth: AcaPyAuthVerified = Depends(acapy_auth_tenant_admin),
) -> List[Tenant]:
    """Get all tenants, or fetch by wallet name and/or group id."""
    bound_logger = logger.bind(body={"wallet_name": wallet_name, "group_id": group_id})
    bound_logger.info(
        "GET request received: Fetch tenants by wallet name and/or group id"
    )

    async with get_tenant_admin_controller() as admin_controller:
        if not (group_id or wallet_name):
            bound_logger.info(
                "No wallet name or group id specified; fetching all wallets"
            )
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

        bound_logger.info("Fetching wallets by wallet name and/or group id")
        wallets = await admin_controller.multitenancy.get_wallets(
            wallet_name=wallet_name, group_id=group_id
        )

    if not wallets.results:
        bound_logger.info("No wallets found for requested wallet name and/or group id.")
        return []

    response = [
        tenant_from_wallet_record(wallet_record) for wallet_record in wallets.results
    ]
    bound_logger.info("Successfully fetched wallets by wallet name and/or group id.")
    return response
