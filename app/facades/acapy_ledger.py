import logging
from typing import Optional, Tuple

from aiohttp import ClientResponseError
from aries_cloudcontroller import (AcaPyClient,
                                   CredentialDefinitionSendRequest, TAAAccept,
                                   TAAInfo, TAARecord,
                                   TxnOrRegisterLedgerNymResponse)

from app.error.cloud_api_error import CloudApiException

logger = logging.getLogger(__name__)


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
    taa_response = await controller.ledger.fetch_taa()
    logger.info("taa_response:\n %s", taa_response)
    if isinstance(taa_response, TAAInfo) or isinstance(taa_response.result, TAAInfo):
        if taa_response.result:
            taa_response = taa_response.result
        mechanism = (
            taa_response.taa_accepted.mechanism
            if taa_response.taa_accepted
            else "service_agreement"
        )
        if not taa_response.taa_record and taa_response.taa_required:
            logger.error("Failed to get TAA. Received response:\n%s", taa_response)
            raise CloudApiException("Something went wrong. Could not get TAA.")
        return taa_response, mechanism
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
    accept_taa_response = await controller.ledger.accept_taa(
        body=TAAAccept(**taa.dict(), mechanism=mechanism)
    )

    if accept_taa_response != {}:
        logger.debug(
            "Failed to accept TAA. Response received:\n%s", accept_taa_response
        )
        raise CloudApiException("Something went wrong. Could not accept TAA.", 400)
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
    issuer_endpoint_response = await controller.ledger.get_did_endpoint(did=issuer_nym)
    if not issuer_endpoint_response:
        logger.debug("Failed to get DID endpoint:\n %s", issuer_endpoint_response)
        raise CloudApiException("Could not obtain issuer endpoint.", 404)
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
    # return the result so we can extract the transaction data
    try:
        return await aries_controller.ledger.register_nym(
            did=did,
            verkey=verkey,
            alias=alias,
            role=role,
            conn_id=connection_id,
            create_transaction_for_endorser=create_transaction_for_endorser,
        )
    except ClientResponseError as e:
        logger.warning(
            "A ClientResponseError was caught while registering NYM. The error message is: '%s'",
            e.message,
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

    write_cred_response = await controller.credential_definition.publish_cred_def(
        body=CredentialDefinitionSendRequest(
            schema_id=schema_id, tag="default", support_revocation=support_revocation
        )
    )
    if not write_cred_response.credential_definition_id:
        logger.warning(
            "Response from `publish_cred_def` did not contain 'credential_definition_id'"
        )
        raise CloudApiException(
            "Something went wrong. Could not write credential definition to the ledger"
        )
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
    # scrape schema id or sequence number from cred def id
    tokens = credential_definition_id.split(":")
    if len(tokens) == 8:  # node protocol >= 1.4: cred def id has 5 or 8 tokens
        return ":".join(tokens[3:7])  # schema id spans 0-based positions 3-6

    # get txn by sequence number, retrieve schema identifier components
    seq_no = tokens[3]

    schema = await controller.schema.get_schema(schema_id=seq_no)

    if not schema.schema_ or not schema.schema_.id:
        raise CloudApiException(f"Schema with id {seq_no} not found", 404)

    return schema.schema_.id
