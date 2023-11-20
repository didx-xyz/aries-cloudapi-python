from typing import Optional, Tuple

from aries_cloudcontroller import (
    AcaPyClient,
    ApiException,
    CredentialDefinitionSendRequest,
    SchemaGetResult,
    TAAAccept,
    TAAInfo,
    TAARecord,
    TxnOrRegisterLedgerNymResponse,
)

from app.exceptions import CloudApiException
from shared.log_config import get_logger

logger = get_logger(__name__)


async def get_taa(controller: AcaPyClient) -> Tuple[TAARecord, str]:
    """
    Obtains the TAA from the ledger

    Parameters:
    -----------
    controller: AcaPyClient
        The aries_cloudcontroller object

    Returns:
    --------
    taa: dict
        The TAA object
    """
    logger.info("Fetching TAA")
    taa_response = await controller.ledger.fetch_taa()
    logger.debug("TTA Response: `{}`", taa_response)
    if isinstance(taa_response, TAAInfo) or isinstance(taa_response.result, TAAInfo):
        if taa_response.result:
            taa_response = taa_response.result
        mechanism = (
            taa_response.taa_accepted.mechanism
            if taa_response.taa_accepted
            else "service_agreement"
        )
        if not taa_response.taa_record and taa_response.taa_required:
            logger.error("Failed to get TAA. Received response: `{}`.", taa_response)
            raise CloudApiException("Something went wrong. Could not get TAA.")
        return taa_response, mechanism

    logger.info("Successfully fetched TAA.")
    return taa_response, "service_agreement"


async def accept_taa(
    controller: AcaPyClient, taa: TAARecord, mechanism: Optional[str] = None
):
    """
    Accept the TAA

    Parameters:
    -----------
    controller: AcaPyClient
        The aries_cloudcontroller object
    TAA:
        The TAA object we want to agree to

    Returns:
    --------
    accept_taa_response: {}
        The response from letting the ledger know we accepted the response
    """
    logger.bind(body=taa).info("Accepting TAA")
    try:
        accept_taa_response = await controller.ledger.accept_taa(
            body=TAAAccept(**taa.to_dict(), mechanism=mechanism)
        )
    except Exception as e:
        logger.exception("An exception occurred while trying to accept TAA.")
        raise CloudApiException(
            "An unexpected error occurred while trying to accept TAA."
        ) from e

    if isinstance(accept_taa_response, ApiException):
        logger.warning(
            "Failed to accept TAA with ApiException. Response: `{}`.",
            accept_taa_response,
        )
        raise CloudApiException("Something went wrong. Could not accept TAA.", 400)

    logger.info("Successfully accepted TAA.")
    return accept_taa_response


async def get_did_endpoint(controller: AcaPyClient, issuer_nym: str):
    """
    Obtains the public DID endpoint

    Parameters:
    -----------
    controller: AcaPyClient
        The aries_cloudcontroller object
    issuer_nym: str
        The issuer's Verinym

    Returns:
    --------
    issuer_endpoint_response: dict
        The response from getting the public endpoint associated with
        the issuer's Verinym from the ledger
    """
    bound_logger = logger.bind(body={"issuer_nym": issuer_nym})
    bound_logger.info("Fetching DID endpoint")

    issuer_endpoint_response = await controller.ledger.get_did_endpoint(did=issuer_nym)
    if not issuer_endpoint_response:
        bound_logger.info("Failed to get DID endpoint; received empty response.")
        raise CloudApiException("Could not obtain issuer endpoint.", 404)
    bound_logger.info("Successfully fetched DID endpoint.")
    return issuer_endpoint_response


async def register_nym_on_ledger(
    aries_controller: AcaPyClient,
    *,
    did: str,
    verkey: str,
    alias: Optional[str] = None,
    role: Optional[str] = None,
    connection_id: Optional[str] = None,
    create_transaction_for_endorser: Optional[str] = None,
) -> TxnOrRegisterLedgerNymResponse:
    bound_logger = logger.bind(body={"did": did})
    bound_logger.info("Registering NYM on ledger")
    try:
        response = await aries_controller.ledger.register_nym(
            did=did,
            verkey=verkey,
            alias=alias,
            role=role,
            conn_id=connection_id,
            create_transaction_for_endorser=create_transaction_for_endorser,
        )
        bound_logger.info("Successfully registered NYM on ledger.")
        return response
    except ApiException as e:
        bound_logger.warning(
            "An ApiException was caught while registering NYM. The error message is: '{}'.",
            e.reason,
        )
        # if not nym_response.success:
        raise CloudApiException("Error registering NYM on ledger.") from e


async def accept_taa_if_required(aries_controller: AcaPyClient):
    taa_response, mechanism = await get_taa(aries_controller)

    if isinstance(taa_response, (TAAInfo, TAARecord)) and taa_response.taa_required:
        await accept_taa(
            aries_controller,
            taa_response.taa_record,
            mechanism,
        )


async def write_credential_def(
    controller: AcaPyClient, schema_id: str, support_revocation: bool = False
) -> str:
    """
    Writes Credential Definition to the ledger

    Parameters:
    ----------
    controller (AcaPyClient): The aries_cloudcontroller object

    schema_id (str): The schema identifier

    support_revocation (bool): Whether to support revocation.
        Default is False

    Returns:
    -------
    write_cred_response :dict
    """
    bound_logger = logger.bind(body={"schema_id": schema_id})
    bound_logger.info("Writing credential definition to the ledger")

    write_cred_response = await controller.credential_definition.publish_cred_def(
        body=CredentialDefinitionSendRequest(
            schema_id=schema_id, tag="default", support_revocation=support_revocation
        )
    )
    if not write_cred_response.credential_definition_id:
        bound_logger.warning(
            "Response from `publish_cred_def` did not contain 'credential_definition_id'."
        )
        raise CloudApiException(
            "Something went wrong. Could not write credential definition to the ledger."
        )
    bound_logger.info("Successfully published credential definition.")
    return write_cred_response.credential_definition_id


async def schema_id_from_credential_definition_id(
    controller: AcaPyClient, credential_definition_id: str
):
    """
    From a credential definition, get the identifier for its schema.

    Taken from ACA-Py implementation:
    https://github.com/hyperledger/aries-cloudagent-python/blob/f9506df755e46c5be93b228c8811276b743a1adc/aries_cloudagent/ledger/indy.py#L790

    Parameters:
    ----------
    credential_definition_id: The identifier of the credential definition
            from which to identify a schema

    Returns:
    -------
    schema_id : string
    """
    bound_logger = logger.bind(
        body={"credential_definition_id": credential_definition_id}
    )
    bound_logger.info("Getting schema id from credential definition id")

    # scrape schema id or sequence number from cred def id
    tokens = credential_definition_id.split(":")
    if len(tokens) == 8:  # node protocol >= 1.4: cred def id has 5 or 8 tokens
        bound_logger.info("Constructed schema id from credential definition.")
        return ":".join(tokens[3:7])  # schema id spans 0-based positions 3-6

    # get txn by sequence number, retrieve schema identifier components
    seq_no = tokens[3]

    bound_logger.debug("Fetching schema using sequence number: `{}`", seq_no)
    schema: SchemaGetResult = await controller.schema.get_schema(schema_id=seq_no)

    if not schema.var_schema or not schema.var_schema.id:
        bound_logger.warning("No schema found with sequence number: `{}`.", seq_no)
        raise CloudApiException(f"Schema with id {seq_no} not found.", 404)

    bound_logger.info("Successfully obtained schema id from credential definition.")
    return schema.var_schema.id
