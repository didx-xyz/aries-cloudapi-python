import logging
from typing import Optional, Union
from aiohttp import ClientResponseError

from aries_cloudcontroller import (
    AcaPyClient,
    IssuerCredRevRecord,
    IssuerRevRegRecord,
    RevRegCreateRequest,
    RevRegResult,
    RevokeRequest,
    TxnOrRevRegResult,
)

from app.error.cloud_api_error import CloudApiException


logger = logging.getLogger(__name__)


async def create_revocation_registry(
    controller: AcaPyClient, credential_definition_id: str, max_cred_num: int = 32767
) -> IssuerRevRegRecord:
    """
        Create a new revocation registry

        This should be called whenever a new credential definition is created.

    Args:
        controller (AcaPyClient): aca-py client
        credential_definition_id (str): The credential definition ID.
        max_cred_num (Optional(int)): The maximum number of credentials to be stored by the registry.
            Default = 32768 (max is 32768)

    Raises:
        Exception: When the credential definition is not found or the revocation registry could not be created.

    Returns:
        result (IssuerRevRegRecord): The revocation registry record.
    """
    result = await controller.revocation.create_registry(
        body=RevRegCreateRequest(
            credential_definition_id=credential_definition_id, max_cred_num=max_cred_num
        )
    )

    if not result.result:
        raise CloudApiException(
            f"Error creating revocation registry for credential with ID {credential_definition_id} and max credential number {max_cred_num}\n{result}"
        )
    
    # result.result.tails_public_uri = 'http://tails-server:6543' # + result.result.revoc_reg_id

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
    result = await controller.revocation.get_active_registry_for_cred_def(
        cred_def_id=credential_definition_id
    )

    if not result.result:
        raise CloudApiException(
            f"Error retrieving revocation registry for credential with ID {credential_definition_id}.\n{result}"
        )

    return result.result


async def get_credential_revocation_status(
    controller: AcaPyClient, credential_exchange_id: str
) -> IssuerCredRevRecord:
    """
        Get the active revocation registry for a credential

    Args:
        controller (AcaPyClient): aca-py client
        credential_definition_id (str): The credential definition ID.

    Raises:
        Exception: When the active revocation registry cannot be retrieved.

    Returns:
        IssuerRevRegRecord: The revocation registry record.
    """
    result = await controller.revocation.get_revocation_status(
        cred_ex_id=credential_exchange_id
    )

    if not result.result:
        credential_definition_id = _get_credential_definition_id_from_exchange_id(
            controller=controller, credential_exchange_id=credential_exchange_id
        )

        raise CloudApiException(
            f"Error retrieving revocation status for credential with ID {credential_definition_id}.\n{result}"
        )

    return result.result


async def publish_revocation_registry_on_ledger(
    controller: AcaPyClient,
    revocation_registry_id: str,
    connection_id: Optional[str] = None,
    create_transaction_for_endorser: Optional[bool] = False,
) -> Union[IssuerRevRegRecord, TxnOrRevRegResult]:
    """
        Publish a created revocation registry to the ledger

    Args:
        controller (AcaPyClient): aca-py client
        revocation_registry_id (str): The revocation registry ID.
        connection_id (str): The connection ID of author to endorser.
        create_transaction_for_endorser (bool): Whether to create a transaction
            record to for the endorser to be endorsed.

    Raises:
        Exception: When the revocation registry could not be published.

    Returns:
        result (Union[IssuerRevRegRecord, TxnOrRevRegResult]): The revocation registry record,
            or the Revocation Register Result and the associated transaction record.
    """
    result = await controller.revocation.publish_rev_reg_def(
        rev_reg_id=revocation_registry_id,
        conn_id=connection_id,
        create_transaction_for_endorser=create_transaction_for_endorser,
    )
    # if create_transaction_for_endorser:
    #     # Tenant issuer wants to write to ledger
    #     assert isinstance(result.result, TxnOrRevRegResult)
    #     governance_controller: AcaPyClient = await get_governance_controller()
    #     await governance_controller.endorse_transaction.endorse_transaction(result.result.txn.transaction_id)

    if isinstance(result, RevRegResult) and result.result:
        is_error = False
        result = result.result
    elif isinstance(result, TxnOrRevRegResult) and result.sent and result.txn:
        is_error = False
    else:
        is_error = True

    if is_error:
        raise CloudApiException(
            f"Failed to publish revocation registry to ledger.\n{result}"
        )

    return result


async def publish_revocation_entry_to_ledger(
    controller: AcaPyClient,
    revocation_registry_id: str = None,
    credential_definition_id: str = None,
    connection_id: str = None,
    create_transaction_for_endorser: bool = False,
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
    if not revocation_registry_id and not credential_definition_id:
        raise CloudApiException(
            "Please, provide either a revocation registry id OR credential definition id."
        )
    if not revocation_registry_id:
        revocation_registry_id = await get_active_revocation_registry_for_credential(
            controller=controller, credential_definition_id=credential_definition_id
        )
    result = await controller.revocation.publish_rev_reg_entry(
        rev_reg_id=revocation_registry_id,
        conn_id=connection_id,
        create_transaction_for_endorser=create_transaction_for_endorser,
    )

    if not result.result:
        raise CloudApiException(
            f"Failed to publish revocation entry to ledger.\n{result}"
        )

    return result.result


async def revoke_credential(
    controller: AcaPyClient,
    credential_exchange_id: str,
    auto_publish_to_ledger: bool = True,
) -> None:
    """
        Revoke an issued credential

    Args:
        controller (AcaPyClient): aca-py client
        credential_exchange_id (str): The credential exchange ID.
        auto_publish_to_ledger (bool): Whether to directly publish the revocation to the ledger.
            Default is False

    Raises:
        Exception: When the credential could not be revoked

    Returns:
        result (None): Successful execution returns None.
    """
    result = await controller.revocation.revoke_credential(
        body=RevokeRequest(
            cred_ex_id=credential_exchange_id, publish=auto_publish_to_ledger
        )
    )

    if result != {}:
        raise CloudApiException(f"Failed to revoke credential.\n{result}")

    if not auto_publish_to_ledger:
        credential_definition_id = await _get_credential_definition_id_from_exchange_id(
            controller=controller, credential_exchange_id=credential_exchange_id
        )

        if not credential_definition_id:
            raise CloudApiException(
                "Failed to retrieve credential definition ID.",
                "Credential revoked but not written to ledger.",
            )

        active_revocation_registry_id = (
            await get_active_revocation_registry_for_credential(
                controller=controller, credential_definition_id=credential_definition_id
            )
        )

        # Publish the revocation to ledger
        await publish_revocation_entry_to_ledger(
            controller=controller,
            revocation_registry_id=active_revocation_registry_id.revoc_reg_id,
        )
    return None


async def _get_credential_definition_id_from_exchange_id(
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
    try:
        credential_definition_id = (
            await controller.issue_credential_v1_0.get_record(
                cred_ex_id=credential_exchange_id
            )
        ).credential_definition_id
    except ClientResponseError:
        rev_reg_parts = (
            await controller.issue_credential_v2_0.get_record(
                cred_ex_id=credential_exchange_id
            )
        ).indy.rev_reg_id.split(":")
        credential_definition_id = [
            rev_reg_parts[2],
            "3",
            "CL",  # TODO: Determine and potentially replace this with other possible signature type
            rev_reg_parts[-4],
            rev_reg_parts[-1],
        ].join(":")
    except Exception:
        credential_definition_id = None
    return credential_definition_id
