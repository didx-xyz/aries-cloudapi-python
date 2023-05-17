import logging
from typing import List, Optional

from aries_cloudcontroller import AcaPyClient, InvitationCreateRequest
from aries_cloudcontroller.model.create_wallet_token_request import \
    CreateWalletTokenRequest
from fastapi.exceptions import HTTPException
from pydantic import BaseModel
from pydantic.networks import AnyHttpUrl

from app.admin.tenants.models import UpdateTenantRequest
from app.constants import ACAPY_ENDORSER_ALIAS
from app.dependencies import (Role, get_governance_controller,
                              get_tenant_controller)
from app.error import CloudApiException
from app.facades import acapy_ledger, acapy_wallet
from app.facades.trust_registry import (TrustRegistryRole, actor_by_id,
                                        update_actor)
from app.listener import Listener
from app.util.did import qualified_did_sov

logger = logging.getLogger(__name__)


class OnboardResult(BaseModel):
    did: str
    didcomm_invitation: Optional[AnyHttpUrl]


def create_listener(topic: str, wallet_id: str) -> Listener:
    # Helper method for passing MockListener to class
    return Listener(topic=topic, wallet_id=wallet_id)


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
        issuer_did = await onboard_issuer_no_public_did(
            name, endorser_controller, issuer_controller, issuer_wallet_id
        )

    # Create an invitation as well
    invitation = await issuer_controller.out_of_band.create_invitation(
        auto_accept=True,
        multi_use=True,
        body=InvitationCreateRequest(
            alias=f"Trust Registry {name}",
            handshake_protocols=["https://didcomm.org/didexchange/1.0"],
        ),
    )

    return OnboardResult(
        did=qualified_did_sov(issuer_did.did),
        didcomm_invitation=invitation.invitation_url,
    )


async def onboard_issuer_no_public_did(
    name: str,
    endorser_controller: AcaPyClient,
    issuer_controller: AcaPyClient,
    issuer_wallet_id: str,
):
    """
    Onboard an issuer without a public DID.

    This function handles the case where the issuer does not have a public DID.
    It takes care of the following steps:
      - Create an endorser invitation using the endorser_controller
      - Wait for the connection between issuer and endorser to complete
      - Set roles for both issuer and endorser
      - Configure endorsement for the connection
      - Register the issuer DID on the ledger

    Args:
        name (str): Name of the issuer
        endorser_controller (AcaPyClient): Authenticated ACA-Py client for endorser
        issuer_controller (AcaPyClient): Authenticated ACA-Py client for issuer
        issuer_wallet_id (str): Wallet id of the issuer

    Returns:
        issuer_did (DID): The issuer's DID after completing the onboarding process
    """

    async def create_endorser_invitation():
        # Make sure the issuer has a connection with the endorser
        invitation = await endorser_controller.out_of_band.create_invitation(
            auto_accept=True,
            body=InvitationCreateRequest(
                alias=name,
                handshake_protocols=["https://didcomm.org/didexchange/1.0"],
                use_public_did=True,
            ),
        )
        return invitation

    async def wait_for_connection_completion(invitation):
        logger.debug(
            f"Starting webhook listener for connections with wallet id {issuer_wallet_id}"
        )

        connections_listener = create_listener(topic="connections", wallet_id="admin")

        # FIXME: make sure the connection with this alias doesn't exist yet
        # Or does use_existing_connection take care of this?
        connection_record = await issuer_controller.out_of_band.receive_invitation(
            auto_accept=True,
            use_existing_connection=True,
            body=invitation.invitation,
            alias=ACAPY_ENDORSER_ALIAS,
        )

        try:
            endorser_connection = await connections_listener.wait_for_filtered_event(
                filter_map={
                    "invitation_msg_id": invitation.invi_msg_id,
                    "state": "completed",
                }
            )
        except TimeoutError as e:
            raise CloudApiException(
                "Timeout occurred while waiting for connection with endorser to complete",
                504,
            ) from e
        finally:
            connections_listener.stop()

        return endorser_connection, connection_record

    async def set_endorser_roles(endorser_connection, connection_record):
        await endorser_controller.endorse_transaction.set_endorser_role(
            conn_id=endorser_connection["connection_id"],
            transaction_my_job="TRANSACTION_ENDORSER",
        )

        await issuer_controller.endorse_transaction.set_endorser_role(
            conn_id=connection_record.connection_id,
            transaction_my_job="TRANSACTION_AUTHOR",
        )

    async def configure_endorsement(connection_record, endorser_did):
        # Make sure endorsement has been configured
        # There is currently no way to retrieve endorser info. We'll just set it
        # to make sure the endorser info is set.
        await issuer_controller.endorse_transaction.set_endorser_info(
            conn_id=connection_record.connection_id,
            endorser_did=endorser_did.did,
        )

    async def register_issuer_did():
        issuer_did = await acapy_wallet.create_did(issuer_controller)

        await acapy_ledger.register_nym_on_ledger(
            endorser_controller,
            did=issuer_did.did,
            verkey=issuer_did.verkey,
            alias=name,
        )

        await acapy_ledger.accept_taa_if_required(issuer_controller)
        # NOTE: Still needs endorsement in 0.7.5 release
        # Otherwise did has no associated services.
        await acapy_wallet.set_public_did(
            issuer_controller,
            did=issuer_did.did,
            create_transaction_for_endorser=True,
        )

        endorsements_listener = create_listener(topic="endorsements", wallet_id="admin")

        try:
            txn_record = await endorsements_listener.wait_for_filtered_event(
                filter_map={
                    "state": "request-received",
                }
            )
        except TimeoutError as e:
            raise CloudApiException(
                "Timeout occured while waiting to create connection with endorser", 504
            ) from e
        finally:
            endorsements_listener.stop()

        await endorser_controller.endorse_transaction.endorse_transaction(
            tran_id=txn_record["transaction_id"]
        )

        return issuer_did

    async def create_connection_with_endorser(endorser_did):
        invitation = await create_endorser_invitation()
        endorser_connection, connection_record = await wait_for_connection_completion(
            invitation
        )
        await set_endorser_roles(endorser_connection, connection_record)
        await configure_endorsement(connection_record, endorser_did)
        issuer_did = await register_issuer_did()

        return issuer_did

    try:
        endorser_did = await acapy_wallet.get_public_did(controller=endorser_controller)
    except Exception as e:
        raise CloudApiException("Unable to get endorser public DID", 500) from e

    try:
        issuer_did = await create_connection_with_endorser(endorser_did)
    except Exception as e:
        raise CloudApiException("Error creating connection with endorser", 500) from e

    return issuer_did


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
