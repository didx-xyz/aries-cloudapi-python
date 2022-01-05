import logging

from aries_cloudcontroller import AcaPyClient
from aries_cloudcontroller.model.did import DID
from aries_cloudcontroller.model.did_create import DIDCreate
from app.error import CloudApiException

logger = logging.getLogger(__name__)


async def assert_public_did(aries_controller: AcaPyClient) -> str:
    """assert the agent has a public did, throwing an error otherwise.

    Args:
        aries_controller (AcaPyClient): the aca-py client.

    Returns:
        str: the public did formatted as fully qualified did
    """
    # Assert the agent has a public did
    public_did = await aries_controller.wallet.get_public_did()

    if not public_did.result or not public_did.result.did:
        raise CloudApiException(
            "Agent has no public did",
            403,
        )

    return f"did:sov:{public_did.result.did}"


async def create_did(controller: AcaPyClient) -> DID:
    """Create a local did

    Args:
        controller (AcaPyClient): [description]

    Raises:
        HTTPException: If the creation of the did failed

    Returns:
        DID: The created did
    """
    generate_did_res = await controller.wallet.create_did(body=DIDCreate())

    if not generate_did_res.result:
        logger.error("Failed to create DID:\n %s", generate_did_res)
        raise CloudApiException(f"Error creating did: {generate_did_res.dict()}", 500)

    return generate_did_res.result


async def set_public_did(controller: AcaPyClient, did: str) -> DID:
    """Set the public did.

    Args:
        controller (AcaPyClient): aca-py client
        did (str): the did to set as public

    Raises:
        CloudApiException: if registration of the public did failed

    Returns:
        DID: the did
    """
    result = await controller.wallet.set_public_did(did=did)

    if not result.result:
        raise CloudApiException(f"Error setting public did: {did}")

    return result.result


async def get_public_did(controller: AcaPyClient) -> DID:
    """Get the public did.

    Args:
        controller (AcaPyClient): aca-py client

    Raises:
        CloudApiException: if retrieving the public did failed.

    Returns:
        DID: the public did
    """
    result = await controller.wallet.get_public_did()

    if not result.result:
        raise CloudApiException("No public did found", 404)

    return result.result
