from aries_cloudcontroller import (
    AcaPyClient,
    InvitationCreateRequest,
    InvitationRecord,
    OobRecord,
)

from app.event_handling.sse_listener import SseListener
from app.exceptions.cloud_api_error import CloudApiException
from app.models.tenants import OnboardResult
from app.services import acapy_ledger, acapy_wallet
from app.services.acapy_wallet import Did
from app.services.onboarding.util import (
    set_author_role,
    set_endorser_info,
    set_endorser_role,
)
from app.util.did import qualified_did_sov
from shared import ACAPY_ENDORSER_ALIAS
from shared.log_config import get_logger

logger = get_logger(__name__)


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
        issuer_did: acapy_wallet.Did = await onboard_issuer_no_public_did(
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

    async def wait_for_connection_completion(invitation: InvitationRecord):
        connections_listener = create_sse_listener(
            topic="connections", wallet_id="admin"
        )

        bound_logger.debug("Receive invitation from endorser on behalf of issuer")
        connection_record = await issuer_controller.out_of_band.receive_invitation(
            auto_accept=True,
            use_existing_connection=False,
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

    async def set_endorser_roles(
        endorser_connection_id: str, issuer_connection_id: str
    ):
        bound_logger.debug("Setting roles for endorser")
        await set_endorser_role(
            endorser_controller, endorser_connection_id, bound_logger
        )

        bound_logger.debug("Setting roles for author")
        await set_author_role(issuer_controller, issuer_connection_id, bound_logger)

        bound_logger.debug("Successfully set roles for connection.")

    async def configure_endorsement(connection_record: OobRecord, endorser_did: str):
        # Make sure endorsement has been configured
        # There is currently no way to retrieve endorser info. We'll just set it
        # to make sure the endorser info is set.
        bound_logger.debug("Setting endorser info")
        await set_endorser_info(
            issuer_controller,
            connection_record.connection_id,
            endorser_did,
            bound_logger,
        )
        bound_logger.debug("Successfully set endorser info.")

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

    async def create_connection_with_endorser(endorser_did: Did):
        invitation = await create_endorser_invitation()
        endorser_connection, connection_record = await wait_for_connection_completion(
            invitation
        )
        await set_endorser_roles(
            endorser_connection["connection_id"], connection_record.connection_id
        )
        await configure_endorsement(connection_record, endorser_did.did)

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
        raise CloudApiException(
            f"Error creating connection with endorser: {str(e)}",
        ) from e

    bound_logger.info("Successfully registered DID for issuer.")
    return issuer_did


def create_sse_listener(wallet_id: str, topic: str) -> SseListener:
    # Helper method for passing a MockListener to a class
    return SseListener(topic=topic, wallet_id=wallet_id)
