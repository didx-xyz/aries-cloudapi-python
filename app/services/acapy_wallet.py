from typing import Optional

from aries_cloudcontroller import DID, AcaPyClient, DIDCreate

from app.exceptions import CloudApiException, handle_acapy_call
from app.util.did import qualified_did_sov
from shared.log_config import get_logger

logger = get_logger(__name__)


async def assert_public_did(aries_controller: AcaPyClient) -> str:
    """assert the agent has a public did, throwing an error otherwise.

    Args:
        aries_controller (AcaPyClient): the aca-py client.

    Returns:
        str: the public did formatted as fully qualified did
    """
    # Assert the agent has a public did
    logger.debug("Fetching public DID")
    public_did = await handle_acapy_call(
        logger=logger, acapy_call=aries_controller.wallet.get_public_did
    )

    if not public_did.result or not public_did.result.did:
        raise CloudApiException("Agent has no public did.", 403)

    logger.debug("Successfully fetched public DID.")

    return qualified_did_sov(public_did.result.did)


async def create_did(
    controller: AcaPyClient, did_create: Optional[DIDCreate] = None
) -> DID:
    """Create a local did

    Args:
        controller (AcaPyClient): [description]

    Raises:
        HTTPException: If the creation of the did failed

    Returns:
        DID: The created did
    """
    logger.debug("Creating local DID")

    if did_create is None:
        did_create = DIDCreate()

    did_response = await handle_acapy_call(
        logger=logger, acapy_call=controller.wallet.create_did, body=did_create
    )

    result = did_response.result
    if not result or not result.did or not result.verkey:
        logger.error("Failed to create DID: `{}`.", did_response)
        raise CloudApiException("Error creating did.")

    logger.debug("Successfully created local DID.")
    return result


async def set_public_did(
    controller: AcaPyClient,
    did: str,
    connection_id: str = None,
    create_transaction_for_endorser: bool = False,
) -> DID:
    """Set the public did.

    Args:
        controller (AcaPyClient): aca-py client
        did (str): the did to set as public

    Raises:
        CloudApiException: if registration of the public did failed

    Returns:
        DID: the did
    """
    logger.debug("Setting public DID")
    did_response = await handle_acapy_call(
        logger=logger,
        acapy_call=controller.wallet.set_public_did,
        did=did,
        conn_id=connection_id,
        create_transaction_for_endorser=create_transaction_for_endorser,
    )

    result = did_response.result
    if not result and not create_transaction_for_endorser:
        raise CloudApiException(f"Error setting public did to `{did}`.", 400)

    logger.debug("Successfully set public DID.")
    return result


async def get_public_did(controller: AcaPyClient) -> DID:
    """Get the public did.

    Args:
        controller (AcaPyClient): aca-py client

    Raises:
        CloudApiException: if retrieving the public did failed.

    Returns:
        DID: the public did
    """
    logger.debug("Fetching public DID")
    did_response = await handle_acapy_call(
        logger=logger, acapy_call=controller.wallet.get_public_did
    )

    result = did_response.result
    if not result:
        raise CloudApiException("No public did found", 404)

    logger.debug("Successfully fetched public DID.")
    return result
