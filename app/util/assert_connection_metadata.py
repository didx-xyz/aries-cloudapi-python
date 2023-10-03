import asyncio
from typing import Callable
from aiohttp import ClientResponseError

from aries_cloudcontroller import AcaPyClient

from app.exceptions.cloud_api_error import CloudApiException

DEFAULT_RETRIES = 10
DEFAULT_DELAY = 0.1


async def assert_metadata_set(
    controller: AcaPyClient,
    conn_id: str,
    check_fn: Callable,
    retries=DEFAULT_RETRIES,
    delay=DEFAULT_DELAY,
):
    """Checks if connection record metadata has been set according to a custom check function.

    Args:
        controller: The AcaPyClient instance for the respective agent
        conn_id: Connection id of the connection you're interested in
        check_fn: A function that takes the metadata and returns True if it meets the desired condition
        retries: Number of retries before failing
        delay: Delay in seconds between each retry

    Returns:
        True if condition is met, raises an exception otherwise.
    """
    for _ in range(retries):
        # Delay is placed at the start to avoid race condition in ACA-Py, where reading metadata causes duplicate
        # record error if metadata is still due to be updated
        await asyncio.sleep(delay)
        try:
            connection_metadata = await controller.connection.get_metadata(
                conn_id=conn_id
            )
            metadata_dict = connection_metadata.results
            if check_fn(metadata_dict):
                return True
        except ClientResponseError:
            # A duplicate record error (aries_cloudagent.storage.error.StorageDuplicateError) may occur in ACA-Py
            # if we fetch metadata while it's being updated
            pass

    raise CloudApiException(
        f"Failed to assert that metadata meets the desired condition after {retries} attempts."
    )


async def assert_endorser_role_set(
    controller, conn_id, retries=DEFAULT_RETRIES, delay=DEFAULT_DELAY
):
    check_fn = (
        lambda metadata: metadata.get("transaction_jobs", {}).get("transaction_my_job")
        == "TRANSACTION_ENDORSER"
    )
    try:
        await assert_metadata_set(controller, conn_id, check_fn, retries, delay)
    except CloudApiException:
        raise CloudApiException(
            "Failed to assert that the endorser role has been set in the connection metadata."
        )


async def assert_author_role_set(
    controller, conn_id, retries=DEFAULT_RETRIES, delay=DEFAULT_DELAY
):
    check_fn = (
        lambda metadata: metadata.get("transaction_jobs", {}).get("transaction_my_job")
        == "TRANSACTION_AUTHOR"
        and metadata.get("transaction_jobs", {}).get("transaction_their_job")
        == "TRANSACTION_ENDORSER"
    )
    try:
        await assert_metadata_set(controller, conn_id, check_fn, retries, delay)
    except CloudApiException:
        raise CloudApiException(
            "Failed to assert that the author role has been set in the connection metadata."
        )


async def assert_endorser_info_set(
    controller, conn_id, endorser_did, retries=DEFAULT_RETRIES, delay=DEFAULT_DELAY
):
    check_fn = (
        lambda metadata: metadata.get("transaction_jobs", {}).get("transaction_my_job")
        == "TRANSACTION_AUTHOR"
        and metadata.get("transaction_jobs", {}).get("transaction_their_job")
        == "TRANSACTION_ENDORSER"
        and metadata.get("endorser_info", {}).get("endorser_did") == endorser_did
    )
    try:
        await assert_metadata_set(controller, conn_id, check_fn, retries, delay)
    except CloudApiException:
        raise CloudApiException(
            "Failed to assert that the endorser info has been set in the connection metadata."
        )
