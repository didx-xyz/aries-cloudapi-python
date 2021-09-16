import logging
from typing import List, TypeVar

from aries_cloudcontroller import (
    AcaPyClient,
    SchemaGetResult,
    CredentialDefinitionSendRequest,
    CredentialPreview,
    SchemaSendRequest,
    V10CredentialProposalRequestMand,
    V10PresentationSendRequestRequest,
)


from fastapi import HTTPException
from pydantic.main import BaseModel

T_co = TypeVar("T_co", contravariant=True)
logger = logging.getLogger(__name__)


class SchemaDefinition(BaseModel):
    name: str
    attributes: List[str]
    version: str


async def get_schema_attributes(controller: AcaPyClient, schema_id: str):
    """
    Obtains Schema Attributes

    Parameters:
    ----------
    controller: AcaPyClient
        The aries_cloudcontroller object

    Returns
    -------
    schema_attr :dict
    """

    schema_resp: SchemaGetResult = await controller.schema.get_schema(
        schema_id=schema_id
    )
    if not schema_resp or not schema_resp.schema_:
        raise HTTPException(
            status_code=404, detail="Could not find schema from provided ID"
        )

    schema_attr = schema_resp.schema_.attr_names
    return schema_attr


async def write_credential_def(controller: AcaPyClient, schema_id: str) -> str:
    """
    Writes Credential Definition to the ledger

    Parameters:
    ----------
    controller: AcaPyClient
        The aries_cloudcontroller object

    Schema id

    Returns:
    -------
    write_cred_response :dict
    """

    write_cred_response = await controller.credential_definition.publish_cred_def(
        body=CredentialDefinitionSendRequest(
            schema_id=schema_id, tag="default", support_revocation=False
        )
    )
    if not write_cred_response.credential_definition_id:
        raise HTTPException(
            status_code=404,
            detail="Something went wrong. Could not write credential definition to the ledger",
        )
    return write_cred_response


async def issue_credentials(
    controller: AcaPyClient,
    connection_id: str,
    schema_id: str,
    cred_def_id: str,
    credential_attributes: CredentialPreview,
):
    record = await controller.issue_credential_v1_0.issue_credential_automated(
        body=V10CredentialProposalRequestMand(
            connection_id=connection_id,
            schema_id=schema_id,
            cred_def_id=cred_def_id,
            credential_proposal=CredentialPreview(attributes=credential_attributes),
            auto_remove=False,
            trace=False,
        )
    )

    if not record:
        raise HTTPException(
            status_code=404, detail="Something went wrong. Unable to issue credential."
        )
    # TODO DO we want to return the credential or just SUCCESS ?
    return record


async def get_connection_id(controller: AcaPyClient):
    """
    Obtains list existing connection ids

    Parameters:
    -----------
    controller: AcaPyClient
        The aries_cloudcontroller object

    Returns:
    -------
    connections: ConnectionList
        List of existing connections in
    """
    connections = await controller.connection.get_connections()
    if not connections:
        raise HTTPException(
            status_code=404, detail="Something went wrong. Could not obtain connections"
        )
    # TODO Return only the active connection id??
    return connections


async def get_schema_list(controller: AcaPyClient):
    """
    Obtains list of existing schemas

    Parameters:
    -----------
    controller: AcaPyClient
        The aries_cloudcontroller object

    Returns
    -------
    created_schemas : SchemasCreatesResult
        List of schemas
    """
    created_schemas = await controller.schema.get_created_schemas()
    if not created_schemas:
        raise HTTPException(
            status_code=404, detail="Something went wrong. Could not obtain schema list"
        )
    return created_schemas


async def write_schema_definition(
    controller: AcaPyClient, schema_definition_request: SchemaDefinition
):
    """
    Writes schema definition to the ledger

    Parameters:
    -----------
    controller: AcaPyClient
        The aries_cloudcontroller object

    schema_definition_request: SchemaDefinition
        Contains the schema name,schema version, schema attributes

    Returns:
    --------
    write_schema_resp : SchemaSendResult

    """
    write_schema_resp = await controller.schema.publish_schema(
        body=SchemaSendRequest(
            attributes=schema_definition_request.attributes,
            name=schema_definition_request.name,
            schema_version=schema_definition_request.version,
        )
    )

    if not write_schema_resp or not write_schema_resp.sent:
        raise HTTPException(
            status_code=404,
            detail=f"Something went wrong.\n Could not write schema to ledger.\n{schema_definition_request}",
        )
    return write_schema_resp.sent


# Need to rename this?
async def verify_proof_req(controller: AcaPyClient, presentation_exchange_id: str):
    verify = await controller.present_proof_v1_0.verify_presentation(
        pres_ex_id=presentation_exchange_id
    )

    if not verify:
        raise HTTPException(
            status_code=404,
            detail="Something went wrong. Could not verify proof request",
        )

    return verify


async def send_proof_request(
    controller: AcaPyClient,
    proof_request_web_request: V10PresentationSendRequestRequest,
):
    response = await controller.present_proof_v1_0.send_request_free(
        body=proof_request_web_request
    )

    if not response:
        raise HTTPException(
            status_code=404, detail="Something went wrong. Could not send proof request"
        )

    return response
