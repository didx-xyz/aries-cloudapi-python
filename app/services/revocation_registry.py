from typing import Optional

from aries_cloudcontroller import (
    AcaPyClient,
    ApiException,
    ClearPendingRevocationsRequest,
    CredRevRecordResult,
    IssuerCredRevRecord,
    IssuerRevRegRecord,
    PublishRevocations,
    RevokeRequest,
    RevRegCreateRequest,
    RevRegResult,
    TransactionRecord,
    TxnOrRevRegResult,
)

from app.dependencies.acapy_clients import get_governance_controller
from app.event_handling.sse_listener import SseListener
from app.exceptions import CloudApiException
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
        body={
            "credential_definition_id": credential_definition_id,
            "max_cred_num": max_cred_num,
        }
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
    bound_logger = logger.bind(
        body={"credential_definition_id": credential_definition_id}
    )
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
    bound_logger = logger.bind(body={"credential_exchange_id": credential_exchange_id})
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
        result TransactionRecord: The transaction record or the Revocation Register Result.
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
            "credential_definition_id": credential_definition_id,
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
    credential_definition_id: str = None,
    auto_publish_to_ledger: bool = False,
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
            "credential_exchange_id": credential_exchange_id,
            "credential_definition_id": credential_definition_id,
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
    except ApiException as e:
        bound_logger.exception(
            "An ApiException was caught while revoking credential. The error message is: '{}'.",
            e.reason,
        )
        raise CloudApiException(
            f"Failed to revoke credential: {e.reason}.", e.status
        ) from e

    bound_logger.info("Successfully revoked credential.")


async def publish_pending_revocations(
    controller: AcaPyClient, rrid2crid: PublishRevocations
):
    """
        Publish pending revocations

    Args:
        controller (AcaPyClient): aca-py client
        rrid2crid (PublishRevocations): The revocation registry ID.

    Raises:
        Exception: When the pending revocations could not be published

    """
    bound_logger = logger.bind(body=rrid2crid)

    bound_logger.info("Validating revocation registry ids")
    await validate_rev_reg_ids(controller=controller, request=rrid2crid)

    try:
        await controller.revocation.publish_revocations(
            body=PublishRevocations(rrid2crid=rrid2crid)
        )
    except ApiException as e:
        bound_logger.exception(
            "An ApiException was caught while publishing pending revocations. The error message is: '{}'.",
            e.reason,
        )
        raise CloudApiException(
            f"Failed to publish pending revocations: {e.reason}.", e.status
        ) from e

    bound_logger.info("Successfully published pending revocations.")


async def clear_pending_revocations(
    controller: AcaPyClient, purge: ClearPendingRevocationsRequest
) -> PublishRevocations:
    """
        Clear pending revocations

    Args:
        controller (AcaPyClient): aca-py client
        purge (ClearPendingRevocationsRequest): The revocation registry ID.

    Raises:
        Exception: When the pending revocations could not be cleared

    """
    bound_logger = logger.bind(body=purge)

    bound_logger.info("Validating revocation registry ids")
    await validate_rev_reg_ids(controller=controller, request=purge)

    try:
        result = await controller.revocation.clear_pending_revocations(
            body=ClearPendingRevocationsRequest(purge=purge)
        )
    except ApiException as e:
        bound_logger.exception(
            "An ApiException was caught while clearing pending revocations. The error message is: '{}'.",
            e.reason,
        )
        raise CloudApiException(
            f"Failed to clear pending revocations: {e.reason}.", e.status
        ) from e

    bound_logger.info("Successfully cleared pending revocations.")
    return result


async def get_credential_revocation_record(
    controller: AcaPyClient,
    credential_exchange_id: str,
    credential_revocation_id: str,
    revocation_registry_id: str,
) -> IssuerCredRevRecord:
    """
        Get the revocation status for a credential

    Args:
        controller (AcaPyClient): aca-py client
        credential_exchange_id (str): The credential exchange ID.
        credential_revocation_id (str): The credential revocation ID.
        revocation_registry_id (str): The revocation registry ID.

    Raises:
        Exception: When failed to get revocation status.

    """
    bound_logger = logger.bind(
        body={
            "credential_exchange_id": credential_exchange_id,
            "credential_revocation_id": credential_revocation_id,
            "revocation_registry_id": revocation_registry_id,
        }
    )
    bound_logger.info("Fetching the revocation status for a credential exchange")

    try:
        result = await controller.revocation.get_revocation_status(
            cred_ex_id=credential_exchange_id if credential_exchange_id else None,
            cred_rev_id=credential_revocation_id if credential_revocation_id else None,
            rev_reg_id=revocation_registry_id if revocation_registry_id else None,
        )
    except ApiException as e:
        bound_logger.exception(
            "An ApiException was caught while getting revocation status. The error message is: '{}'.",
            e.reason,
        )
        raise CloudApiException(
            f"Failed to get revocation status: {e.reason}.", e.status
        ) from e

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


async def get_credential_definition_id_from_exchange_id(
    controller: AcaPyClient, credential_exchange_id: str
) -> Optional[str]:
    """
        Get the credential definition id from the credential exchange id.

    Args:
        controller (AcaPyClient): aca-py client
        credential_exchange_id (RevokeRequest): The credential exchange ID.

    Returns:
        credential_definition_id (Optional[str]): The credential definition ID or None.
    """
    bound_logger = logger.bind(body={"credential_exchange_id": credential_exchange_id})
    bound_logger.info("Fetching credential definition id from exchange id")

    try:
        credential_definition_id = (
            await controller.issue_credential_v1_0.get_record(
                cred_ex_id=credential_exchange_id
            )
        ).credential_definition_id
    except ApiException as err1:
        bound_logger.info(
            "An ApiException was caught while getting v1 record. The error message is: '{}'",
            err1.reason,
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
        except ApiException as err2:
            bound_logger.info(
                "An ApiException was caught while getting v2 record. The error message is: '{}'",
                err2.reason,
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


async def validate_rev_reg_ids(controller: AcaPyClient, request: dict):
    """
        Validate revocation registry ids

    Args:
        controller (AcaPyClient): aca-py client
        request (dict): The request body.

    Raises:
        Exception: When the revocation registry ids are invalid.

    """
    bound_logger = logger.bind(body=request)
    bound_logger.info("Validating revocation registry ids")
    rev_reg_id_list = list(request.keys())

    if len(rev_reg_id_list) > 0:
        try:
            for key in rev_reg_id_list:
                result_count = (
                    await controller.revocation.get_registry_issued_credentials_count(
                        rev_reg_id=key
                    )
                )
                bound_logger.debug(result_count)
        except ApiException as e:

            if e.status == 404:
                bound_logger.info(
                    "The rev_reg_id does not exist '{}'.",
                    e.reason,
                )
                raise CloudApiException(
                    f"The rev_reg_id does not exist: {e.reason}.", e.status
                ) from e
            else:
                bound_logger.error(
                    "An ApiException was caught while validating rev_reg_id. The error message is: '{}'.",
                    e.reason,
                )
                raise CloudApiException(f"{e.reason}.", e.status) from e

    bound_logger.info("Successfully validated revocation registry ids.")
