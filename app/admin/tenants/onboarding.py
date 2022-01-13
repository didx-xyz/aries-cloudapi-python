from typing import Optional, Set
from aries_cloudcontroller import (
    AcaPyClient,
    InvitationCreateRequest,
)
from aries_cloudcontroller.model.create_wallet_token_request import (
    CreateWalletTokenRequest,
)
from fastapi.exceptions import HTTPException
from pydantic import BaseModel
from pydantic.networks import AnyHttpUrl
from app.admin.tenants.models import UpdateTenantRequest
from app.dependencies import Role, get_tenant_controller, get_yoma_controller
from app.facades.trust_registry import (
    TrustRegistryRole,
    actor_by_id,
    update_actor,
)

from app.error import CloudApiException
from app.facades import acapy_ledger, acapy_wallet, acapy_connections
from app.util.did import qualified_did_sov


class OnboardResult(BaseModel):
    did: str
    didcomm_invitation: Optional[AnyHttpUrl]


async def handle_ecosystem_tenant_update(
    admin_controller: AcaPyClient,
    tenant_id: str,
    update: UpdateTenantRequest,
):
    # We retrieve the wallet to verify what has changed
    wallet = await admin_controller.multitenancy.get_wallet(wallet_id=tenant_id)

    # Get tenant from trust registry
    actor = await actor_by_id(wallet.wallet_id)

    if not actor:
        raise HTTPException(
            404, f"actor with id {tenant_id} not registered in trust registry"
        )

    if actor:
        updated_actor = actor.copy()

        if update.name:
            actor["name"] = update.name

        if update.roles:

            # We only care about the added roles, as that's what needs the setup.
            # Teardown is not required at the moment, besides from removing it from
            # the trust registry
            added_roles = update.roles - set(actor["roles"])

            # We need to pose as the tenant to onboard for the specified role
            token_response = await admin_controller.multitenancy.get_auth_token(
                wallet_id=tenant_id, body=CreateWalletTokenRequest()
            )

            onboard_result = await onboard_ecosystem_tenant(
                name=actor["name"],
                roles=added_roles,
                tenant_auth_token=token_response.token,
            )

            actor["roles"] = list(update.roles)
            actor["did"] = onboard_result.did
            actor["didcomm_invitation"] = onboard_result.didcomm_invitation

        await update_actor(updated_actor)


async def onboard_ecosystem_tenant(
    *, name: str, roles: Set[TrustRegistryRole], tenant_auth_token: str
) -> OnboardResult:
    if TrustRegistryRole.ISSUER in roles:
        # Get yoma and tenant controllers, onboard issuer
        async with get_yoma_controller() as yoma_controller, get_tenant_controller(
            Role.ECOSYSTEM, tenant_auth_token
        ) as tenant_controller:
            return await onboard_issuer(
                name=name,
                issuer_controller=tenant_controller,
                endorser_controller=yoma_controller,
            )

    elif TrustRegistryRole.VERIFIER in roles:
        async with get_tenant_controller(
            Role.ECOSYSTEM, tenant_auth_token
        ) as tenant_controller:
            return await onboard_verifier(
                name=name, verifier_controller=tenant_controller
            )

    raise CloudApiException("Unable to onboard tenant without role(s).")


async def onboard_issuer(
    *, name: str, issuer_controller: AcaPyClient, endorser_controller: AcaPyClient
):
    """Onboard the controller as issuer.

    The onboarding will take care of the following:
      - make sure the issuer has a public did
      - make sure the issuer has a connection with the endorser
      - make sure the issuer has set up endorsement with the endorser connection

    Args:
        name (str): name of the issuer
        issuer_controller (AcaPyClient): authenticated ACA-Py client for issuer
        endorser_controller (AcaPyClient): authenticated ACA-Py client for endorser
    """
    # Make sure the issuer has a public did
    try:
        issuer_did = await acapy_wallet.get_public_did(issuer_controller)
    except CloudApiException:
        # no public did
        issuer_did = await acapy_wallet.create_did(issuer_controller)
        await acapy_ledger.register_nym_on_ledger(
            endorser_controller,
            did=issuer_did.did,
            verkey=issuer_did.verkey,
            alias=name,
        )
        await acapy_ledger.accept_taa_if_required(issuer_controller)
        await acapy_wallet.set_public_did(issuer_controller, issuer_did.did)

    endorser_did = await acapy_wallet.get_public_did(endorser_controller)

    # Make sure the issuer has a connection with the endorser
    connections = await acapy_connections.get_connections_by_invitation_key(
        issuer_controller, endorser_did.verkey
    )

    if connections and len(connections) > 0:
        connection_record = connections[0]
    else:
        # Make sure the issuer has a connection with the endorser
        invitation = await endorser_controller.out_of_band.create_invitation(
            auto_accept=True,
            body=InvitationCreateRequest(
                alias=name,
                handshake_protocols=["https://didcomm.org/didexchange/1.0"],
                use_public_did=True,
            ),
        )

        connection_record = await issuer_controller.out_of_band.receive_invitation(
            # FIXME: remove hardcoded yoma here
            alias="Yoma",
            auto_accept=True,
            body=invitation.invitation,
        )

    await issuer_controller.endorse_transaction.set_endorser_role(
        conn_id=connection_record.connection_id, transaction_my_job="TRANSACTION_AUTHOR"
    )

    # FIXME: do we need to wait for the connection to complete?
    # Make sure endorsement has been configured
    # There is currently no way to retrieve endorser info. We'll just set it
    # to make sure the endorser info is set.
    await issuer_controller.endorse_transaction.set_endorser_info(
        conn_id=connection_record.connection_id,
        # FIXME: remove hardcoded yoma here
        endorser_name="Yoma",
        endorser_did=endorser_did.did,
    )

    return OnboardResult(did=qualified_did_sov(issuer_did.did))


async def onboard_verifier(*, name: str, verifier_controller: AcaPyClient):
    """Onboard the controller as verifier.

    The onboarding will take care of the following:
      - create a multi_use invitation to use in the

    Args:
        verifier_controller (AcaPyClient): authenticated ACA-Py client for verifier
    """

    # If the verifier already has a public did it doesn't need an invitation. The invitation
    # is just to bypass having to pay for a public did for every verifier
    try:
        public_did = await acapy_wallet.get_public_did(verifier_controller)

        return OnboardResult(did=qualified_did_sov(public_did.did))
    except CloudApiException:
        # create a multi_use invitation from the did
        invitation = await verifier_controller.out_of_band.create_invitation(
            auto_accept=True,
            multi_use=True,
            body=InvitationCreateRequest(
                use_public_did=False,
                alias=f"Trust Registry {name}",
                handshake_protocols=["https://didcomm.org/didexchange/1.0"],
            ),
        )

        try:
            did_key = invitation.invitation.services[0]["recipientKeys"][0]
        except KeyError as e:
            # FIXME: more verbose error
            raise CloudApiException(f"Error creating invitation: {e}")

        return OnboardResult(
            did=did_key,
            didcomm_invitation=invitation.invitation_url,
        )
