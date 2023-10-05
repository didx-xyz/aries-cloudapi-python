import asyncio
from logging import Logger
from typing import Callable

from aiohttp import ClientResponseError
from aries_cloudcontroller import AcaPyClient

from app.exceptions.cloud_api_error import CloudApiException

DEFAULT_NUM_TRIES = 10
DEFAULT_DELAY = 0.2


async def set_endorser_role(
    endorser_controller: AcaPyClient, endorser_connection_id: str, logger: Logger
):
    delay = DEFAULT_DELAY
    for n in range(DEFAULT_NUM_TRIES):
        try:
            logger.debug(
                f"Setting roles for endorser on endorser-issuer connection. Try: {n}"
            )
            await endorser_controller.endorse_transaction.set_endorser_role(
                conn_id=endorser_connection_id,
                transaction_my_job="TRANSACTION_ENDORSER",
            )

            # Try assert that it's done. Checking too soon may raise ACA-Py error (bug).
            # So if it fails, retry with backing-off delay
            logger.debug("Assert that the endorser role is set before continuing")
            await assert_endorser_role_set(
                endorser_controller,
                endorser_connection_id,
                logger,
                num_tries=1,
                delay=delay,
            )
            logger.debug(f"Successfully set endorser role on try: {n}")
            return True  # success, exit retries
        except (SettingMetadataException, ClientResponseError) as e:
            if n == DEFAULT_NUM_TRIES:
                logger.error(
                    "Failed to set endorser role after {} retries.", DEFAULT_NUM_TRIES
                )
                raise CloudApiException(
                    "Failed to set the endorser role in the endorser-issuer connection, "
                    f"with connection id {endorser_connection_id}."
                ) from e
        logger.warning(
            f"Setting endorser role has failed on try {n} with delay {delay}s"
        )
        await asyncio.sleep(delay)  # Secondary delay. Primary occurs in assert_ method

        delay *= 2
        logger.info(f"Retry setting of endorser role with increased delay: {delay}s")


async def set_author_role(
    issuer_controller: AcaPyClient, issuer_connection_id: str, logger: Logger
):
    delay = DEFAULT_DELAY
    for n in range(DEFAULT_NUM_TRIES):
        try:
            logger.debug(
                f"Setting roles for author on issuer-endorser connection. Try: {n}"
            )
            await issuer_controller.endorse_transaction.set_endorser_role(
                conn_id=issuer_connection_id,
                transaction_my_job="TRANSACTION_AUTHOR",
            )

            # Try assert that it's done. Checking too soon may raise ACA-Py error (bug).
            # So if it fails, retry with backing-off delay
            logger.debug("Assert that the author role is set before continuing")

            await assert_author_role_set(
                issuer_controller,
                issuer_connection_id,
                logger,
                num_tries=1,
                delay=delay,
            )
            logger.debug(f"Successfully set author role on try: {n}")
            return True  # success, exit retries
        except (SettingMetadataException, ClientResponseError) as e:
            if n == DEFAULT_NUM_TRIES:
                logger.error(
                    "Failed to set author role after {} retries.", DEFAULT_NUM_TRIES
                )
                raise CloudApiException(
                    "Failed to set the author role in the issuer-endorser connection, "
                    f"with connection id {issuer_connection_id}."
                ) from e
        logger.warning(f"Setting author role has failed on try {n} with delay {delay}s")
        await asyncio.sleep(delay)  # Secondary delay. Primary occurs in assert_ method

        delay *= 2
        logger.info(f"Retry setting of author role with increased delay: {delay}s")


async def set_endorser_info(
    issuer_controller: AcaPyClient,
    issuer_connection_id: str,
    endorser_did: str,
    logger: Logger,
):
    delay = DEFAULT_DELAY
    for n in range(DEFAULT_NUM_TRIES):
        try:
            logger.debug(
                f"Setting endorser info on issuer-endorser connection. Try: {n}"
            )
            await issuer_controller.endorse_transaction.set_endorser_info(
                conn_id=issuer_connection_id,
                endorser_did=endorser_did,
            )

            # Try assert that it's done. Checking too soon may raise ACA-Py error (bug).
            # So if it fails, retry with backing-off delay
            logger.debug("Assert that the endorser info is set before continuing")

            await assert_endorser_info_set(
                issuer_controller,
                issuer_connection_id,
                endorser_did,
                logger,
                num_tries=1,
                delay=delay,
            )
            logger.debug(f"Successfully set author role on try: {n}")
            return True  # success, exit retries
        except (SettingMetadataException, ClientResponseError) as e:
            if n == DEFAULT_NUM_TRIES:
                logger.error(
                    "Failed to set endorser info after {} retries.", DEFAULT_NUM_TRIES
                )
                raise CloudApiException(
                    "Failed to set the endorser info in the issuer-endorser connection, "
                    f"with connection id {issuer_connection_id}."
                ) from e
        logger.warning(
            f"Setting endorser info has failed on try {n} with delay {delay}s"
        )
        await asyncio.sleep(delay)  # Secondary delay. Primary occurs in assert_ method

        delay *= 2
        logger.info(f"Retry setting of endorser info with increased delay: {delay}s")


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
