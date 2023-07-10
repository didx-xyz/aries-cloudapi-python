from typing import Optional, Union

from aiohttp import ClientResponseError
from aries_cloudcontroller import (
    AcaPyClient,
    CredRevRecordResult,
    IssuerCredRevRecord,
    IssuerRevRegRecord,
    RevokeRequest,
    RevRegCreateRequest,
    RevRegResult,
    TransactionRecord,
    TxnOrRevRegResult,
)

from app.dependencies.acapy_clients import get_governance_controller
from app.event_handling.sse_listener import SseListener
from app.exceptions.cloud_api_error import CloudApiException
from shared.log_config import get_logger

logger = get_logger(__name__)


async def create_revocation_registry(
    controller: AcaPyClient, credential_definition_id: str, max_cred_num: int = 32767
) -> IssuerRevRegRecord:
    """
        Create a new revocation registry

        This should be called whenever a new credential definition is created.

    Args:
        controller (AcaPyClient): aca-py client
        credential_definition_id (str): The credential definition ID.
        max_cred_num (int): The maximum number of credentials to be stored by the registry.
            Default = 32768 (i.e. max is 32768)

    Raises:
        Exception: When the credential definition is not found or the revocation registry could not be created.

    Returns:
        result (IssuerRevRegRecord): The revocation registry record.
    """
    bound_logger = logger.bind(
        body={"cred_def_id": credential_definition_id, "max_cred_num": max_cred_num}
    )
    bound_logger.info("Creating a new revocation registry for a credential definition")
    result = await controller.revocation.create_registry(
        body=RevRegCreateRequest(
            credential_definition_id=credential_definition_id, max_cred_num=max_cred_num
        )
    )

    if not result:
        bound_logger.error("Error creating revocation registry.")
        raise CloudApiException(
            f"Error creating revocation registry for credential with ID `{credential_definition_id}`."
        )

    bound_logger.info("Successfully created revocation registry.")

    return result.result


async def get_active_revocation_registry_for_credential(
    controller: AcaPyClient, credential_definition_id: str
) -> IssuerRevRegRecord:
    """
        Get the active revocation registry for a credential

    Args:
        controller (AcaPyClient): aca-py client
        credential_definition_id (str): The credential definition ID.

    Raises:
        Exception: When the active revocation registry cannot be retrieved.

    Returns:
        result (IssuerRevRegRecord): The revocation registry record.
    """
    bound_logger = logger.bind(body={"cred_def_id": credential_definition_id})
    bound_logger.info("Fetching activate revocation registry for a credential")

    result = await controller.revocation.get_active_registry_for_cred_def(
        cred_def_id=credential_definition_id
    )

    if not isinstance(result, RevRegResult):
        bound_logger.error(
            "Unexpected type returned from get_active_registry_for_cred_def: `{}`.",
            result,
        )
        raise CloudApiException(
            f"Error retrieving revocation registry for credential with ID `{credential_definition_id}`."
        )

    bound_logger.info(
        "Successfully retrieved revocation registry for credential definition."
    )
    return result.result


async def get_credential_revocation_status(
    controller: AcaPyClient, credential_exchange_id: str
) -> IssuerCredRevRecord:
    """
        Get the revocation status for a credential

    Args:
        controller (AcaPyClient): aca-py client
        credential_exchange_id (str): The credential exchange ID.

    Raises:
        Exception: When the active revocation registry cannot be retrieved.

    Returns:
        IssuerCredRevRecord: The revocation registry record.
    """
    bound_logger = logger.bind(body={"cred_ex_id": credential_exchange_id})
    bound_logger.info("Fetching the revocation status for a credential exchange")

    result = await controller.revocation.get_revocation_status(
        cred_ex_id=credential_exchange_id
    )

    if not isinstance(result, CredRevRecordResult):
        bound_logger.error(
            "Unexpected type returned from get_revocation_status: `{}`.", result
        )
        raise CloudApiException(
            f"Error retrieving revocation status for credential exchange ID `{credential_exchange_id}`."
        )
    else:
        result = result.result

    bound_logger.info("Successfully retrieved revocation status.")
    return result


async def publish_revocation_registry_on_ledger(
    controller: AcaPyClient,
    revocation_registry_id: str,
    connection_id: Optional[str] = None,
    create_transaction_for_endorser: bool = False,
) -> TransactionRecord:
    """
        Publish a created revocation registry to the ledger

    Args:
        controller (AcaPyClient): aca-py client
        revocation_registry_id (str): The revocation registry ID.
        connection_id (Optional[str]): The connection ID of author to endorser.
        create_transaction_for_endorser (bool): Whether to create a transaction
            record to for the endorser to be endorsed.

    Raises:
        Exception: When the revocation registry could not be published.

    Returns:
        result TxnOrRevRegResult: The transaction record or the Revocation Register Result.
    """
    bound_logger = logger.bind(
        body={
            "revocation_registry_id": revocation_registry_id,
            "connection_id": connection_id,
            "create_transaction_for_endorser": create_transaction_for_endorser,
        }
    )
    bound_logger.info("Publishing revocation registry to the ledger")

    txn_or_rev_reg_result = await controller.revocation.publish_rev_reg_def(
        rev_reg_id=revocation_registry_id,
        conn_id=connection_id if create_transaction_for_endorser else None,
        create_transaction_for_endorser=create_transaction_for_endorser,
    )

    if isinstance(txn_or_rev_reg_result, RevRegResult):
        result = txn_or_rev_reg_result.result
    elif (
        isinstance(txn_or_rev_reg_result, TxnOrRevRegResult)
        and txn_or_rev_reg_result.txn
    ):
        result = txn_or_rev_reg_result.txn
    else:
        bound_logger.error(
            "Unexpected type returned from publish_rev_reg_def: `{}`.",
            txn_or_rev_reg_result,
        )
        raise CloudApiException("Failed to publish revocation registry to ledger.")

    bound_logger.info("Successfully published revocation registry to ledger.")

    return result


async def publish_revocation_entry_to_ledger(
    controller: AcaPyClient,
    revocation_registry_id: Optional[str] = None,
    credential_definition_id: Optional[str] = None,
    connection_id: Optional[str] = None,
    create_transaction_for_endorser: Optional[bool] = False,
) -> IssuerRevRegRecord:
    """
        Publish a created revocation entry to the ledger

    Args:
        controller (AcaPyClient): aca-py client
        credential_definition_id (str): The credential definition ID.
        revocation_registry_id (str): The revocation registry ID.
            Default is None
        connection_id (str): The connection ID of author to endorser.
            Default is None
        create_transaction_for_endorser (bool): Whether to create a transaction
            record to for the endorser to be endorsed.
            Default is False

    Raises:
        Exception: When the revocation registry entry could not be published.

    Returns:
        result (IssuerRevRegRecord): The revocation registry record.
    """
    bound_logger = logger.bind(
        body={
            "revocation_registry_id": revocation_registry_id,
            "cred_def_id": credential_definition_id,
            "connection_id": connection_id,
            "create_transaction_for_endorser": create_transaction_for_endorser,
        }
    )
    bound_logger.info("Publishing revocation entry to the ledger")

    if not revocation_registry_id and not credential_definition_id:
        bound_logger.info(
            "Bad request: one of `revocation_registry_id` or `credential_definition_id` must be given"
        )
        raise CloudApiException(
            "Invalid request. Please provide either a 'revocation registry id' or a 'credential definition id'.",
            400,
        )
    if not revocation_registry_id:
        bound_logger.debug("Fetching active revocation registry for credential")
        revocation_registry_id = await get_active_revocation_registry_for_credential(
            controller=controller, credential_definition_id=credential_definition_id
        )
    try:
        bound_logger.debug("Publishing revocation entry")
        result = await controller.revocation.publish_rev_reg_entry(
            rev_reg_id=revocation_registry_id,
            conn_id=connection_id if create_transaction_for_endorser else None,
            create_transaction_for_endorser=create_transaction_for_endorser,
        )
    except Exception as e:
        bound_logger.exception("An unexpected exception occurred.")
        return e

    if not isinstance(result, RevRegResult):
        bound_logger.error(
            "Unexpected type returned from publish_rev_reg_entry: `{}`.", result
        )
        raise CloudApiException("Failed to publish revocation entry to ledger.")

    bound_logger.info("Successfully published revocation entry to ledger.")
    return result.result


async def revoke_credential(
    controller: AcaPyClient,
    credential_exchange_id: str,
    auto_publish_to_ledger: bool = False,
    credential_definition_id: str = None,
) -> None:
    """
        Revoke an issued credential

    Args:
        controller (AcaPyClient): aca-py client
        credential_exchange_id (str): The credential exchange ID.
        credential_definition_id (str): The credential definition ID.
        auto_publish_to_ledger (bool): Whether to directly publish the revocation to the ledger.
            This should only be true when invoked by an endorser.
            Default is False

    Raises:
        Exception: When the credential could not be revoked

    Returns:
        result (None): Successful execution returns None.
    """
    bound_logger = logger.bind(
        body={
            "cred_ex_id": credential_exchange_id,
            "cred_def_id": credential_definition_id,
            "auto_publish_to_ledger": auto_publish_to_ledger,
        }
    )
    bound_logger.info("Revoking an issued credential")

    try:
        await controller.revocation.revoke_credential(
            body=RevokeRequest(
                cred_ex_id=credential_exchange_id,
                publish=auto_publish_to_ledger,
            )
        )
    except ClientResponseError as e:
        bound_logger.info(
            "A ClientResponseError was caught while revoking credential. The error message is: '{}'.",
            e.message,
        )
        raise CloudApiException("Failed to revoke credential.", 400) from e

    if not auto_publish_to_ledger:
        active_revocation_registry_id = (
            await get_active_revocation_registry_for_credential(
                controller=controller,
                credential_definition_id=credential_definition_id,
            )
        )

        try:
            await publish_revocation_entry_to_ledger(
                controller=controller,
                revocation_registry_id=active_revocation_registry_id.revoc_reg_id,
                create_transaction_for_endorser=True,
            )
        except CloudApiException as e:
            if e.status_code == 400:
                bound_logger.info(
                    "Bad request: Cannot publish revocation entry to ledger: {}",
                    e.detail,
                )
            else:
                bound_logger.error(e.detail)
            raise e
        except Exception as e:
            bound_logger.exception("Exception caught when revoking credential.")
            raise e
            # This is unexpected and throws and error in the controller validating the pydantic model.
            # It still creates the transaction record though that can be endorsed below.
        finally:
            # NB: Adding finally clause, as it seems this must be called no matter what:
            await endorser_revoke()

    bound_logger.info("Successfully revoked credential.")


async def endorser_revoke():
    listener = SseListener(topic="endorsements", wallet_id="admin")
    try:
        logger.debug("Waiting for endorsements event in `request-received` state")
        txn_record = await listener.wait_for_state(desired_state="request-received")
    except TimeoutError as e:
        logger.error("Waiting for an endorsement event has timed out.")
        raise CloudApiException(
            "Timeout occurred while waiting to retrieve transaction record for endorser.",
            504,
        ) from e
    async with get_governance_controller() as endorser_controller:
        logger.info("Endorsing what is presumed to be a revocation transaction")
        await endorser_controller.endorse_transaction.endorse_transaction(
            tran_id=txn_record["transaction_id"]
        )
    logger.info("Successfully endorsed transaction of revocation.")


async def get_credential_definition_id_from_exchange_id(
    controller: AcaPyClient, credential_exchange_id: str
) -> Union[str, None]:
    """
        Get the credential definition id from the credential exchange id.

    Args:
        controller (AcaPyClient): aca-py client
        credential_exchange_id (RevokeRequest): The credential exchange ID.

    Returns:
        credential_definition_id (Union[str,None]): The credential definition ID or None.
    """
    bound_logger = logger.bind(body={"credential_exchange_id": credential_exchange_id})
    bound_logger.info("Fetching credential definition id from exchange id")

    try:
        credential_definition_id = (
            await controller.issue_credential_v1_0.get_record(
                cred_ex_id=credential_exchange_id
            )
        ).credential_definition_id
    except ClientResponseError as e:
        bound_logger.info(
            "A ClientResponseError was caught while getting v1 record. The error message is: '{}'",
            e.message,
        )
        try:
            bound_logger.info("Trying to get v2 records")
            rev_reg_parts = (
                await controller.issue_credential_v2_0.get_record(
                    cred_ex_id=credential_exchange_id
                )
            ).indy.rev_reg_id.split(":")
            credential_definition_id = ":".join(
                [
                    rev_reg_parts[2],
                    "3",
                    "CL",  # NOTE: Potentially replace this with other possible signature type in future
                    rev_reg_parts[-4],
                    rev_reg_parts[-1],
                ]
            )
        except ClientResponseError as e:
            bound_logger.info(
                "A ClientResponseError was caught while getting v2 record. The error message is: '{}'",
                e.message,
            )
            return
        except Exception:
            bound_logger.exception(
                "Exception caught when getting v2 records for cred ex id."
            )
            return

    bound_logger.info(
        "Successfully obtained cred definition id from the cred exchange id."
    )
    return credential_definition_id
