from logging import Logger

from aries_cloudcontroller import AcaPyClient, InvitationCreateRequest, InvitationRecord

from app.event_handling.sse_listener import SseListener
from app.exceptions import CloudApiException
from app.services import acapy_ledger, acapy_wallet
from app.services.acapy_wallet import Did
from app.services.onboarding.util.set_endorser_metadata import (
    set_author_role,
    set_endorser_info,
    set_endorser_role,
)
from shared import ACAPY_ENDORSER_ALIAS


async def create_connection_with_endorser(
    *,
    endorser_controller: AcaPyClient,
    issuer_controller: AcaPyClient,
    endorser_did: Did,
    name: str,
    logger: Logger,
):
    invitation = await create_endorser_invitation(
        endorser_controller=endorser_controller, name=name, logger=logger
    )
    endorser_connection_id, issuer_connection_id = await wait_for_connection_completion(
        issuer_controller=issuer_controller, invitation=invitation, logger=logger
    )
    await set_endorser_roles(
        endorser_controller=endorser_controller,
        issuer_controller=issuer_controller,
        endorser_connection_id=endorser_connection_id,
        issuer_connection_id=issuer_connection_id,
        logger=logger,
    )
    await configure_endorsement(
        issuer_controller=issuer_controller,
        issuer_connection_id=issuer_connection_id,
        endorser_did=endorser_did.did,
        logger=logger,
    )


async def create_endorser_invitation(
    *, endorser_controller: AcaPyClient, name: str, logger: Logger
):
    logger.debug("Create OOB invitation on behalf of endorser")
    invitation = await endorser_controller.out_of_band.create_invitation(
        auto_accept=True,
        body=InvitationCreateRequest(
            alias=name,
            handshake_protocols=["https://didcomm.org/didexchange/1.0"],
            use_public_did=True,
        ),
    )
    logger.debug("Created OOB invitation")
    return invitation


async def wait_for_connection_completion(
    *, issuer_controller: AcaPyClient, invitation: InvitationRecord, logger: Logger
) -> tuple[str, str]:
    connections_listener = create_sse_listener(topic="connections", wallet_id="admin")

    logger.debug("Receive invitation from endorser on behalf of issuer")
    connection_record = await issuer_controller.out_of_band.receive_invitation(
        auto_accept=True,
        use_existing_connection=False,
        body=invitation.invitation,
        alias=ACAPY_ENDORSER_ALIAS,
    )

    try:
        logger.debug("Waiting for event signalling invitation complete")
        endorser_connection = await connections_listener.wait_for_event(
            field="invitation_msg_id",
            field_id=invitation.invi_msg_id,
            desired_state="completed",
        )
    except TimeoutError as e:
        logger.error("Waiting for invitation complete event has timed out.")
        raise CloudApiException(
            "Timeout occurred while waiting for connection with endorser to complete.",
            504,
        ) from e

    logger.info("Connection complete between issuer and endorser.")
    return endorser_connection["connection_id"], connection_record.connection_id


async def set_endorser_roles(
    *,
    endorser_controller: AcaPyClient,
    issuer_controller: AcaPyClient,
    endorser_connection_id: str,
    issuer_connection_id: str,
    logger: Logger,
):
    logger.debug("Setting roles for endorser")
    await set_endorser_role(
        endorser_controller=endorser_controller,
        endorser_connection_id=endorser_connection_id,
        logger=logger,
    )

    logger.debug("Setting roles for author")
    await set_author_role(
        issuer_controller=issuer_controller,
        issuer_connection_id=issuer_connection_id,
        logger=logger,
    )

    logger.debug("Successfully set roles for connection.")


async def configure_endorsement(
    *,
    issuer_controller: AcaPyClient,
    issuer_connection_id: str,
    endorser_did: str,
    logger: Logger,
):
    # Make sure endorsement has been configured
    # There is currently no way to retrieve endorser info. We'll just set it
    # to make sure the endorser info is set.
    logger.debug("Setting endorser info")
    await set_endorser_info(
        issuer_controller=issuer_controller,
        issuer_connection_id=issuer_connection_id,
        endorser_did=endorser_did,
        logger=logger,
    )
    logger.debug("Successfully set endorser info.")


async def register_issuer_did(
    *,
    endorser_controller: AcaPyClient,
    issuer_controller: AcaPyClient,
    issuer_label: str,
    logger: Logger,
):
    logger.info("Creating DID for issuer")
    issuer_did = await acapy_wallet.create_did(issuer_controller)

    await acapy_ledger.register_nym_on_ledger(
        endorser_controller,
        did=issuer_did.did,
        verkey=issuer_did.verkey,
        alias=issuer_label,
    )

    logger.debug("Accepting TAA on behalf of issuer")
    await acapy_ledger.accept_taa_if_required(issuer_controller)
    # NOTE: Still needs endorsement in 0.7.5 release
    # Otherwise did has no associated services.
    logger.debug("Setting public DID for issuer")
    await acapy_wallet.set_public_did(
        issuer_controller,
        did=issuer_did.did,
        create_transaction_for_endorser=True,
    )

    endorsements_listener = create_sse_listener(topic="endorsements", wallet_id="admin")

    try:
        logger.debug("Waiting for endorsement request received")
        txn_record = await endorsements_listener.wait_for_state(
            desired_state="request-received"
        )
    except TimeoutError as e:
        logger.error("Waiting for endorsement request has timed out.")
        raise CloudApiException(
            "Timeout occurred while waiting for endorsement request.", 504
        ) from e

    logger.bind(body=txn_record["transaction_id"]).debug("Endorsing transaction")
    await endorser_controller.endorse_transaction.endorse_transaction(
        tran_id=txn_record["transaction_id"]
    )

    logger.debug("Issuer DID registered and endorsed successfully.")
    return issuer_did


def create_sse_listener(wallet_id: str, topic: str) -> SseListener:
    # Helper method for passing a MockListener to this module in tests
    return SseListener(topic=topic, wallet_id=wallet_id)
