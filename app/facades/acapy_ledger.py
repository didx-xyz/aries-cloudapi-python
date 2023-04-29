import logging
from typing import Optional, Tuple
from aiohttp import ClientResponseError

from aries_cloudcontroller import (
    AcaPyClient,
    CredentialDefinitionSendRequest,
    TAAAccept,
    TAAInfo,
    TAARecord,
    TxnOrRegisterLedgerNymResponse,
)
from fastapi import HTTPException

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
            logger.error("Failed to get TAA:\n %s", taa_response)
            raise HTTPException(
                status_code=404,
                detail=f"Something went wrong. Could not get TAA. {taa_response}",
            )
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

    if isinstance(accept_taa_response, dict):
        # accept_taa_response = accept_taa_response
        logger.info("accept_taa_response - TAA response is type dict %s", accept_taa_response)
    else:
        logger.info("accept_taa_response - TAA response is type something else %s", accept_taa_response)
        accept_taa_response = await accept_taa_response.json()

    logger.info("accept_taa_response: %s", accept_taa_response)
    if accept_taa_response != {}:
        logger.error("Failed to accept TAA.\n %s", accept_taa_response)
        raise HTTPException(
            status_code=404,
            detail=f"Something went wrong. Could not accept TAA. {accept_taa_response}",
        )
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
        logger.error("Failed to get DID endpoint:\n %s", issuer_endpoint_response)
        raise HTTPException(
            status_code=404,
            detail="Something went wrong. Could not obtain issuer endpoint.",
        )
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
        # if not nym_response.success:
        raise HTTPException(500, "Error registering nym on ledger: %s", e)


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
        raise HTTPException(
            status_code=404,
            detail="Something went wrong. Could not write credential definition to the ledger",
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
        raise Exception(f"Schema with transaction number {seq_no} not found")

    return schema.schema_.id
