import logging
from typing import Optional, List
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
from app.dependencies import Role, get_tenant_controller, get_governance_controller
from app.facades.trust_registry import (
    TrustRegistryRole,
    actor_by_id,
    update_actor,
)
from app.constants import ACAPY_ENDORSER_ALIAS
from app.util.did import qualified_did_sov
from app.webhook_listener import start_listener

from app.error import CloudApiException
from app.facades import acapy_ledger, acapy_wallet

logger = logging.getLogger(__name__)


class OnboardResult(BaseModel):
    did: str
    didcomm_invitation: Optional[AnyHttpUrl]


async def handle_tenant_update(
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
            updated_actor["name"] = update.name

        if update.roles:

            # We only care about the added roles, as that's what needs the setup.
            # Teardown is not required at the moment, besides from removing it from
            # the trust registry
            added_roles = list(set(update.roles) - set(actor["roles"]))

            # We need to pose as the tenant to onboard for the specified role
            token_response = await admin_controller.multitenancy.get_auth_token(
                wallet_id=tenant_id, body=CreateWalletTokenRequest()
            )

            onboard_result = await onboard_tenant(
                name=updated_actor["name"],
                roles=added_roles,
                tenant_auth_token=token_response.token,
                tenant_id=tenant_id,
            )

            # Remove duplicates from the role list
            updated_actor["roles"] = list(set(update.roles))
            updated_actor["did"] = onboard_result.did
            updated_actor["didcomm_invitation"] = onboard_result.didcomm_invitation

        await update_actor(updated_actor)


async def onboard_tenant(
    *, name: str, roles: List[TrustRegistryRole], tenant_auth_token: str, tenant_id: str
) -> OnboardResult:
    if "issuer" in roles:
        # Get governance and tenant controllers, onboard issuer
        async with get_governance_controller() as governance_controller, get_tenant_controller(
            Role.TENANT, tenant_auth_token
        ) as tenant_controller:
            return await onboard_issuer(
                name=name,
                endorser_controller=governance_controller,
                issuer_controller=tenant_controller,
                issuer_wallet_id=tenant_id,
            )

    elif "verifier" in roles:
        async with get_tenant_controller(
            Role.TENANT, tenant_auth_token
        ) as tenant_controller:
            return await onboard_verifier(
                name=name, verifier_controller=tenant_controller
            )

    raise CloudApiException("Unable to onboard tenant without role(s).")


async def onboard_issuer(
    *,
    name: str = None,
    endorser_controller: AcaPyClient,
    issuer_controller: AcaPyClient,
    issuer_wallet_id: str,
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

    try:
        issuer_did = await acapy_wallet.get_public_did(controller=issuer_controller)
    except CloudApiException:
        # no public did
        endorser_did = await acapy_wallet.get_public_did(controller=endorser_controller)

        # Make sure the issuer has a connection with the endorser
        invitation = await endorser_controller.out_of_band.create_invitation(
            auto_accept=True,
            body=InvitationCreateRequest(
                alias=name,
                handshake_protocols=["https://didcomm.org/didexchange/1.0"],
                use_public_did=True,
            ),
        )

        logger.info(
            f"Starting webhook listener for connections with wallet id {issuer_wallet_id}"
        )

        endorser_wait_for_connection, _ = await start_listener(
            topic="connections", wallet_id="admin"
        )

        endorser_wait_for_transaction, _ = await start_listener(
            topic="endorsements", wallet_id="admin"
        )

        logger.debug("Receiving connection invitation")

        # FIXME: make sure the connection with this alias doesn't exist yet
        # Or does use_existing_connection take care of this?
        connection_record = await issuer_controller.out_of_band.receive_invitation(
            auto_accept=True,
            use_existing_connection=True,
            body=invitation.invitation,
            alias=ACAPY_ENDORSER_ALIAS,
        )

        logger.debug(
            f"Waiting for connection with id {connection_record.connection_id} to be completed"
        )

        # Wait for connection to be completed before continuing
        try:
            endorser_connection = await endorser_wait_for_connection(
                filter_map={
                    "invitation_msg_id": invitation.invi_msg_id,
                    "state": "completed",
                }
            )

        except TimeoutError:
            raise CloudApiException("Error creating connection with endorser", 500)

        logger.debug("Successfully created connection")

        await endorser_controller.endorse_transaction.set_endorser_role(
            conn_id=endorser_connection["connection_id"],
            transaction_my_job="TRANSACTION_ENDORSER",
        )

        await issuer_controller.endorse_transaction.set_endorser_role(
            conn_id=connection_record.connection_id,
            transaction_my_job="TRANSACTION_AUTHOR",
        )

        # Make sure endorsement has been configured
        # There is currently no way to retrieve endorser info. We'll just set it
        # to make sure the endorser info is set.
        await issuer_controller.endorse_transaction.set_endorser_info(
            conn_id=connection_record.connection_id,
            endorser_did=endorser_did.did,
        )

        issuer_did = await acapy_wallet.create_did(issuer_controller)

        await acapy_ledger.register_nym_on_ledger(
            endorser_controller,
            did=issuer_did.did,
            verkey=issuer_did.verkey,
            alias=name,
        )

        await acapy_ledger.accept_taa_if_required(issuer_controller)
        # TODO: This doesn't need endorsement as of 0.7.5-rc0 onward - bug in 0.7.4
        # Change this in future versions
        await acapy_wallet.set_public_did(
            issuer_controller,
            did=issuer_did.did,
            connection_id=connection_record.connection_id,
            create_transaction_for_endorser=True,
        )

        try:
            txn_record = await endorser_wait_for_transaction(
                filter_map={
                    "state": "request-received",
                }
            )
        except TimeoutError:
            raise CloudApiException("Error creating connection with endorser", 500)

        await endorser_controller.endorse_transaction.endorse_transaction(
            tran_id=txn_record["transaction_id"]
        )

    return OnboardResult(did=qualified_did_sov(issuer_did.did))


async def onboard_verifier(*, name: str, verifier_controller: AcaPyClient):
    """Onboard the controller as verifier.

    The onboarding will take care of the following:
      - create a multi_use invitation to use in the

    Args:
        verifier_controller (AcaPyClient): authenticated ACA-Py client for verifier
    """

    onboarding_result = {}

    # If the verifier already has a public did it doesn't need an invitation. The invitation
    # is just to bypass having to pay for a public did for every verifier
    try:
        public_did = await acapy_wallet.get_public_did(controller=verifier_controller)

        onboarding_result["did"] = qualified_did_sov(public_did.did)
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
            # Because we're not creating an invitation with a public did the invitation will always
            # contain a did:key as the first recipientKey in the first service
            onboarding_result["did"] = invitation.invitation.services[0][
                "recipientKeys"
            ][0]
            onboarding_result["didcomm_invitation"] = invitation.invitation_url
        except (KeyError, IndexError) as e:
            # FIXME: more verbose error
            raise CloudApiException(f"Error creating invitation: {e}")

    return OnboardResult(**onboarding_result)
