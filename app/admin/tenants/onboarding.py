import asyncio
from typing import List, Optional

from aiohttp.web import HTTPForbidden
from aries_cloudcontroller import AcaPyClient, InvitationCreateRequest, InvitationRecord
from aries_cloudcontroller.model.create_wallet_token_request import (
    CreateWalletTokenRequest,
)
from fastapi.exceptions import HTTPException
from pydantic import BaseModel
from pydantic.networks import AnyHttpUrl

from app.admin.tenants.models import UpdateTenantRequest
from app.dependencies.acapy_clients import (
    get_governance_controller,
    get_tenant_controller,
)
from app.event_handling.sse_listener import SseListener
from app.exceptions.cloud_api_error import CloudApiException
from app.facades import acapy_ledger, acapy_wallet
from app.facades.trust_registry import TrustRegistryRole, actor_by_id, update_actor
from app.util.did import qualified_did_sov
from shared import ACAPY_ENDORSER_ALIAS
from shared.log_config import get_logger

logger = get_logger(__name__)


class OnboardResult(BaseModel):
    did: str
    didcomm_invitation: Optional[AnyHttpUrl]


def create_sse_listener(wallet_id: str, topic: str) -> SseListener:
    # Helper method for passing MockListener to class
    return SseListener(topic=topic, wallet_id=wallet_id)


async def handle_tenant_update(
    admin_controller: AcaPyClient,
    tenant_id: str,
    update: UpdateTenantRequest,
):
    bound_logger = logger.bind(body={"tenant_id": tenant_id})
    bound_logger.bind(body=update).info("Handling tenant update")

    bound_logger.debug("Retrieving the wallet")
    wallet = await admin_controller.multitenancy.get_wallet(wallet_id=tenant_id)
    if not wallet:
        bound_logger.error("Bad request: Wallet not found.")
        raise HTTPException(404, f"Wallet for tenant id `{tenant_id}` not found.")

    bound_logger.debug("Retrieving tenant from trust registry")
    actor = await actor_by_id(wallet.wallet_id)
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
    bound_logger.info("Tenant update handled successfully.")


async def onboard_tenant(
    *, name: str, roles: List[TrustRegistryRole], tenant_auth_token: str, tenant_id: str
) -> OnboardResult:
    bound_logger = logger.bind(
        body={"name": name, "roles": roles, "tenant_id": tenant_id}
    )
    bound_logger.bind(body=roles).info("Start onboarding tenant")

    if "issuer" in roles:
        bound_logger.debug("Tenant has 'issuer' role, onboarding as issuer")
        # Get governance and tenant controllers, onboard issuer
        async with get_governance_controller() as governance_controller, get_tenant_controller(
            tenant_auth_token
        ) as tenant_controller:
            onboard_result = await onboard_issuer(
                name=name,
                endorser_controller=governance_controller,
                issuer_controller=tenant_controller,
                issuer_wallet_id=tenant_id,
            )
            bound_logger.info("Onboarding as issuer completed successfully.")
            return onboard_result

    elif "verifier" in roles:
        bound_logger.debug("Tenant has 'verifier' role, onboarding as verifier")
        async with get_tenant_controller(tenant_auth_token) as tenant_controller:
            onboard_result = await onboard_verifier(
                name=name, verifier_controller=tenant_controller
            )
            bound_logger.info("Onboarding as verifier completed successfully.")
            return onboard_result

    bound_logger.error("Tenant request does not have valid role(s) for onboarding.")
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
    bound_logger = logger.bind(body={"issuer_wallet_id": issuer_wallet_id})
    bound_logger.info("Onboarding issuer")

    try:
        issuer_did = await acapy_wallet.get_public_did(controller=issuer_controller)
        bound_logger.debug("Obtained public DID for the to-be issuer")
    except CloudApiException:
        bound_logger.debug("No public DID for the to-be issuer")
        issuer_did = await onboard_issuer_no_public_did(
            name, endorser_controller, issuer_controller, issuer_wallet_id
        )

    bound_logger.debug("Creating OOB invitation on behalf of issuer")
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
    bound_logger = logger.bind(body={"issuer_wallet_id": issuer_wallet_id})
    bound_logger.info("Onboarding issuer that has no public DID")

    async def create_endorser_invitation():
        # Make sure the issuer has a connection with the endorser
        bound_logger.debug("Create OOB invitation on behalf of endorser")
        invitation = await endorser_controller.out_of_band.create_invitation(
            auto_accept=True,
            body=InvitationCreateRequest(
                alias=name,
                handshake_protocols=["https://didcomm.org/didexchange/1.0"],
                use_public_did=True,
            ),
        )
        bound_logger.debug("Created OOB invitation")
        return invitation

    async def wait_for_connection_completion(invitation):
        connections_listener = create_sse_listener(
            topic="connections", wallet_id="admin"
        )

        # FIXME: make sure the connection with this alias doesn't exist yet
        # Or does use_existing_connection take care of this?
        bound_logger.debug("Receive invitation from endorser on behalf of issuer")
        connection_record = await issuer_controller.out_of_band.receive_invitation(
            auto_accept=True,
            use_existing_connection=True,
            body=invitation.invitation,
            alias=ACAPY_ENDORSER_ALIAS,
        )

        try:
            bound_logger.debug("Waiting for event signalling invitation complete")
            endorser_connection = await connections_listener.wait_for_event(
                field="invitation_msg_id",
                field_id=invitation.invi_msg_id,
                desired_state="completed",
            )
        except TimeoutError as e:
            bound_logger.error("Waiting for invitation complete event has timed out.")
            raise CloudApiException(
                "Timeout occurred while waiting for connection with endorser to complete.",
                504,
            ) from e

        bound_logger.info("Connection complete between issuer and endorser.")
        return endorser_connection, connection_record

    async def set_endorser_roles(endorser_connection, connection_record):
        bound_logger.debug("Setting roles for endorser")
        await endorser_controller.endorse_transaction.set_endorser_role(
            conn_id=endorser_connection["connection_id"],
            transaction_my_job="TRANSACTION_ENDORSER",
        )

        await issuer_controller.endorse_transaction.set_endorser_role(
            conn_id=connection_record.connection_id,
            transaction_my_job="TRANSACTION_AUTHOR",
        )
        bound_logger.debug("Successfully set roles for endorser.")

    async def configure_endorsement(connection_record, endorser_did):
        # Make sure endorsement has been configured
        # There is currently no way to retrieve endorser info. We'll just set it
        # to make sure the endorser info is set.
        bound_logger.debug("Setting endorser info")
        await issuer_controller.endorse_transaction.set_endorser_info(
            conn_id=connection_record.connection_id,
            endorser_did=endorser_did.did,
        )
        bound_logger.debug("Successfully set endorser info.")

    async def configure_endorsement_with_retry(connection_record, endorser_did):
        MAX_ATTEMPTS = 3
        RETRY_DELAY = 1.0  # delay in seconds

        for attempt in range(MAX_ATTEMPTS):
            try:
                await configure_endorsement(connection_record, endorser_did)
                break
            except aiohttp.web_exceptions.HTTPForbidden as e:
                if attempt + 1 == MAX_ATTEMPTS:
                    bound_logger.error("Maximum number of retries exceeded. Failing.")
                    raise e  # Re-raise the exception if max attempts exceeded

                bound_logger.warning(
                    f"Failed to set roles (attempt {attempt + 1}). Retrying in {RETRY_DELAY} seconds..."
                )
                await asyncio.sleep(RETRY_DELAY)

    async def register_issuer_did():
        bound_logger.info("Creating DID for issuer")
        issuer_did = await acapy_wallet.create_did(issuer_controller)

        await acapy_ledger.register_nym_on_ledger(
            endorser_controller,
            did=issuer_did.did,
            verkey=issuer_did.verkey,
            alias=name,
        )

        bound_logger.debug("Accepting TAA on behalf of issuer")
        await acapy_ledger.accept_taa_if_required(issuer_controller)
        # NOTE: Still needs endorsement in 0.7.5 release
        # Otherwise did has no associated services.
        bound_logger.debug("Setting public DID for issuer")
        await acapy_wallet.set_public_did(
            issuer_controller,
            did=issuer_did.did,
            create_transaction_for_endorser=True,
        )

        endorsements_listener = create_sse_listener(
            topic="endorsements", wallet_id="admin"
        )

        try:
            bound_logger.debug("Waiting for endorsement request received")
            txn_record = await endorsements_listener.wait_for_state(
                desired_state="request-received"
            )
        except TimeoutError as e:
            bound_logger.error("Waiting for endorsement request has timed out.")
            raise CloudApiException(
                "Timeout occurred while waiting for endorsement request.", 504
            ) from e

        bound_logger.bind(body=txn_record["transaction_id"]).debug(
            "Endorsing transaction"
        )
        await endorser_controller.endorse_transaction.endorse_transaction(
            tran_id=txn_record["transaction_id"]
        )

        bound_logger.debug("Issuer DID registered and endorsed successfully.")
        return issuer_did

    async def create_connection_with_endorser(endorser_did):
        invitation = await create_endorser_invitation()
        endorser_connection, connection_record = await wait_for_connection_completion(
            invitation
        )
        await set_endorser_roles(endorser_connection, connection_record)
        await configure_endorsement_with_retry(connection_record, endorser_did)

    try:
        logger.debug("Getting public DID for endorser")
        endorser_did = await acapy_wallet.get_public_did(controller=endorser_controller)
    except Exception as e:
        logger.critical("Endorser has no public DID.")
        raise CloudApiException("Unable to get endorser public DID.") from e

    try:
        bound_logger.info("Creating connection with endorser")
        await create_connection_with_endorser(endorser_did)
        issuer_did = await register_issuer_did()
    except Exception as e:
        bound_logger.exception("Could not create connection with endorser.")
        raise CloudApiException("Error creating connection with endorser.") from e

    bound_logger.info("Successfully registered DID for issuer.")
    return issuer_did


async def onboard_verifier(*, name: str, verifier_controller: AcaPyClient):
    """Onboard the controller as verifier.

    The onboarding will take care of the following:
      - create a multi_use invitation to use in the

    Args:
        verifier_controller (AcaPyClient): authenticated ACA-Py client for verifier
    """
    bound_logger = logger.bind(body={"name": name})
    bound_logger.info("Onboarding verifier")

    onboarding_result = {}

    # If the verifier already has a public did it doesn't need an invitation. The invitation
    # is just to bypass having to pay for a public did for every verifier
    try:
        bound_logger.debug("Getting public DID for to-be verifier")
        public_did = await acapy_wallet.get_public_did(controller=verifier_controller)

        onboarding_result["did"] = qualified_did_sov(public_did.did)
    except CloudApiException:
        bound_logger.info(
            "No public DID found for to-be verifier. "
            "Creating OOB invitation on their behalf."
        )
        # create a multi_use invitation from the did
        invitation: InvitationRecord = (
            await verifier_controller.out_of_band.create_invitation(
                auto_accept=True,
                multi_use=True,
                body=InvitationCreateRequest(
                    use_public_did=False,
                    alias=f"Trust Registry {name}",
                    handshake_protocols=["https://didcomm.org/didexchange/1.0"],
                ),
            )
        )

        # check if invitation and necessary attributes exist
        if invitation and invitation.invitation and invitation.invitation.services:
            try:
                # Because we're not creating an invitation with a public did the invitation will always
                # contain a did:key as the first recipientKey in the first service
                bound_logger.debug("Getting DID from verifier's invitation")
                service = invitation.invitation.services[0]
                if (
                    service
                    and "recipientKeys" in service
                    and len(service["recipientKeys"]) > 0
                ):
                    onboarding_result["did"] = service["recipientKeys"][0]
                else:
                    raise KeyError(
                        f"RecipientKeys not present in the invitation service: `{service}`."
                    )
                onboarding_result["didcomm_invitation"] = invitation.invitation_url
            except (KeyError, IndexError) as e:
                bound_logger.error(
                    "Created invitation does not contain expected keys: {}", e
                )
                raise CloudApiException(
                    "Error onboarding verifier: No public DID found. "
                    "Tried to create invitation, but found no service/recipientKeys."
                ) from e
        else:
            bound_logger.error(
                "Created invitation does not have necessary attributes. Got: `{}`.",
                invitation,
            )
            raise CloudApiException(
                "Error onboarding verifier: No public DID found. "
                "Tried and failed to create invitation on their behalf."
            )

    bound_logger.info("Returning verifier onboard result.")
    return OnboardResult(**onboarding_result)
