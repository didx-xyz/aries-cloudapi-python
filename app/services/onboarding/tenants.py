from typing import List

from aries_cloudcontroller import AcaPyClient, CreateWalletTokenRequest
from fastapi.exceptions import HTTPException

from app.dependencies.acapy_clients import (
    get_governance_controller,
    get_tenant_controller,
)
from app.exceptions.cloud_api_error import CloudApiException
from app.models.tenants import OnboardResult, UpdateTenantRequest
from app.models.trust_registry import TrustRegistryRole
from app.services.onboarding.issuer import onboard_issuer
from app.services.onboarding.verifier import onboard_verifier
from app.services.trust_registry.actors import fetch_actor_by_id, update_actor
from shared.log_config import get_logger

logger = get_logger(__name__)


async def handle_tenant_update(
    admin_controller: AcaPyClient,
    wallet_id: str,
    update: UpdateTenantRequest,
):
    bound_logger = logger.bind(body={"wallet_id": wallet_id})
    bound_logger.bind(body=update).info("Handling tenant update")

    bound_logger.debug("Retrieving the wallet")
    wallet = await admin_controller.multitenancy.get_wallet(wallet_id=wallet_id)
    if not wallet:
        bound_logger.error("Bad request: Wallet not found.")
        raise HTTPException(404, f"Wallet with id `{wallet_id}` not found.")

    bound_logger.debug("Retrieving tenant from trust registry")
    actor = await fetch_actor_by_id(wallet.wallet_id)
    if not actor:
        bound_logger.error(
            "Tenant not found in trust registry. "
            "Holder tenants cannot be updated with new roles."
        )
        raise HTTPException(409, "Holder tenants cannot be updated with new roles.")

    updated_actor = actor.copy()
    if update.name:
        updated_actor["name"] = update.name

    if update.roles:
        bound_logger.info("Updating tenant roles")
        # We only care about the added roles, as that's what needs the setup.
        # Teardown is not required at the moment, besides from removing it from
        # the trust registry
        added_roles = list(set(update.roles) - set(actor["roles"]))

        # We need to pose as the tenant to onboard for the specified role
        token_response = await admin_controller.multitenancy.get_auth_token(
            wallet_id=wallet_id, body=CreateWalletTokenRequest()
        )

        onboard_result = await onboard_tenant(
            name=updated_actor["name"],
            roles=added_roles,
            wallet_auth_token=token_response.token,
            wallet_id=wallet_id,
        )

        # Remove duplicates from the role list
        updated_actor["roles"] = list(set(update.roles))
        updated_actor["did"] = onboard_result.did
        updated_actor["didcomm_invitation"] = onboard_result.didcomm_invitation

    await update_actor(updated_actor)
    bound_logger.info("Tenant update handled successfully.")


async def onboard_tenant(
    *, name: str, roles: List[TrustRegistryRole], wallet_auth_token: str, wallet_id: str
) -> OnboardResult:
    bound_logger = logger.bind(
        body={"name": name, "roles": roles, "wallet_id": wallet_id}
    )
    bound_logger.bind(body=roles).info("Start onboarding tenant")

    if "issuer" in roles:
        bound_logger.debug("Tenant has 'issuer' role, onboarding as issuer")
        # Get governance and tenant controllers, onboard issuer
        async with get_governance_controller() as governance_controller, get_tenant_controller(
            wallet_auth_token
        ) as tenant_controller:
            onboard_result = await onboard_issuer(
                name=name,
                endorser_controller=governance_controller,
                issuer_controller=tenant_controller,
                issuer_wallet_id=wallet_id,
            )
            bound_logger.info("Onboarding as issuer completed successfully.")
            return onboard_result

    elif "verifier" in roles:
        bound_logger.debug("Tenant has 'verifier' role, onboarding as verifier")
        async with get_tenant_controller(wallet_auth_token) as tenant_controller:
            onboard_result = await onboard_verifier(
                name=name, verifier_controller=tenant_controller
            )
            bound_logger.info("Onboarding as verifier completed successfully.")
            return onboard_result

    bound_logger.error("Tenant request does not have valid role(s) for onboarding.")
    raise CloudApiException("Unable to onboard tenant without role(s).")
