import asyncio
from logging import Logger
from typing import Callable

from aiohttp import ClientResponseError
from aries_cloudcontroller import AcaPyClient

from app.exceptions.cloud_api_error import CloudApiException

DEFAULT_NUM_TRIES = 10
DEFAULT_DELAY = 0.2


async def assert_metadata_set(
    controller: AcaPyClient,
    conn_id: str,
    check_fn: Callable,
    logger: Logger,
    num_tries=DEFAULT_NUM_TRIES,
    delay=DEFAULT_DELAY,
):
    """Checks if connection record metadata has been set according to a custom check function.

    Args:
        controller: The AcaPyClient instance for the respective agent
        conn_id: Connection id of the connection you're interested in
        check_fn: A function that takes the metadata and returns True if it meets the desired condition
        logger: A logger instance
        num_tries: Number of num_tries before failing
        delay: Delay in seconds between each retry

    Returns:
        True if condition is met, raises an exception otherwise.
    """
    for _ in range(num_tries):
        # Delay is placed at the start to avoid race condition in ACA-Py, where reading metadata causes duplicate
        # record error if metadata is still due to be updated
        logger.debug(f"Sleep {delay}s before trying to fetch metadata")
        await asyncio.sleep(delay)
        try:
            logger.debug("Fetching connection metadata")
            connection_metadata = await controller.connection.get_metadata(
                conn_id=conn_id
            )
            logger.debug("Successfully fetched metadata")
            metadata_dict = connection_metadata.results
            if check_fn(metadata_dict):
                return True
        except ClientResponseError as e:
            logger.error("Exception occurred when getting metadata: {}", e)
            pass

    raise SettingMetadataException(
        f"Failed to assert that metadata meets the desired condition after {num_tries} attempts."
    )


async def assert_endorser_role_set(
    controller: AcaPyClient,
    conn_id: str,
    logger: Logger,
    num_tries=1,
    delay=DEFAULT_DELAY,
):
    check_fn = (
        lambda metadata: metadata.get("transaction_jobs", {}).get("transaction_my_job")
        == "TRANSACTION_ENDORSER"
    )
    try:
        await assert_metadata_set(
            controller, conn_id, check_fn, logger, num_tries, delay
        )
    except Exception as e:
        raise SettingMetadataException(
            "Failed to assert that the endorser role has been set in the connection metadata."
        ) from e


async def assert_author_role_set(
    controller: AcaPyClient,
    conn_id: str,
    logger: Logger,
    num_tries=1,
    delay=DEFAULT_DELAY,
):
    check_fn = (
        lambda metadata: metadata.get("transaction_jobs", {}).get("transaction_my_job")
        == "TRANSACTION_AUTHOR"
        and metadata.get("transaction_jobs", {}).get("transaction_their_job")
        == "TRANSACTION_ENDORSER"
    )
    try:
        await assert_metadata_set(
            controller, conn_id, check_fn, logger, num_tries, delay
        )
    except Exception as e:
        raise SettingMetadataException(
            "Failed to assert that the author role has been set in the connection metadata."
        ) from e


async def assert_endorser_info_set(
    controller: AcaPyClient,
    conn_id: str,
    endorser_did: str,
    logger: Logger,
    num_tries=1,
    delay=DEFAULT_DELAY,
):
    check_fn = (
        lambda metadata: metadata.get("transaction_jobs", {}).get("transaction_my_job")
        == "TRANSACTION_AUTHOR"
        and metadata.get("transaction_jobs", {}).get("transaction_their_job")
        == "TRANSACTION_ENDORSER"
        and metadata.get("endorser_info", {}).get("endorser_did") == endorser_did
    )
    try:
        await assert_metadata_set(
            controller, conn_id, check_fn, logger, num_tries, delay
        )
    except Exception as e:
        raise SettingMetadataException(
            "Failed to assert that the endorser info has been set in the connection metadata."
        ) from e


class SettingMetadataException(CloudApiException):
    pass
