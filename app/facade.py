import logging

from typing import TypeVar

from fastapi import HTTPException

T_co = TypeVar("T_co", contravariant=True)
logger = logging.getLogger(__name__)


async def get_schema_attributes(controller, schema_id):
    """
    Obtains Schema Attributes

    Parameters:
    ----------
    controller: AriesController
        The aries_cloudcontroller object

    Returns
    -------
    schema_attr :dict
    """

    schema_resp = await controller.schema.get_by_id(schema_id)
    if not schema_resp:
        raise HTTPException(
            status_code=404, detail="Could not find schema from provided ID"
        )
    schema_attr = schema_resp["schema"]["attrNames"]
    return schema_attr


async def write_credential_def(controller, schema_id):
    """
    Writes Credential Definition to the ledger

    Parameters:
    ----------
    controller: AriesController
        The aries_cloudcontroller object

    Schema id

    Returns:
    -------
    write_cred_response :dict
    """

    write_cred_response = await controller.definitions.write_cred_def(schema_id)
    if not write_cred_response:
        raise HTTPException(
            status_code=404,
            detail="Something went wrong. Could not write credential definition to the ledger",
        )
    return write_cred_response


async def get_cred_def_id(controller, credential_def):
    """
    Obtains the credential definition id

    Parameters:
    ----------
    controller: AriesController
        The aries_cloudcontroller object

    credential_def : The credential definition whose id we wish to obtain

    Returns:
    -------
    cred_def_id : dict
        The credential definition id
    """

    # TODO Determine what is funky here?!
    cred_def_id = credential_def["credential_definition_id"]
    if not cred_def_id:
        raise HTTPException(
            status_code=404,
            detail="Something went wrong. Could not find credential definition id from the provided credential definition",
        )
    return cred_def_id


async def issue_credentials(
    controller, connection_id, schema_id, cred_def_id, credential_attributes
):
    record = await controller.issuer.send_credential(
        connection_id, schema_id, cred_def_id, credential_attributes, trace=False
    )
    if not record:
        raise HTTPException(
            status_code=404, detail="Something went wrong. Unable to issue credential."
        )
    # TODO DO we want to return the credential or just SUCCESS ?
    return record


async def get_connection_id(controller):
    """
    Obtains list existing connection ids

    Parameters:
    -----------
    controller: AriesController
        The aries_cloudcontroller object

    Returns:
    -------
    connections: dict
        List of existing connections in
    """
    connections = await controller.connections.get_connections()
    if not connections:
        raise HTTPException(
            status_code=404, detail="Something went wrong. Could not obtain connections"
        )
    # TODO Return only the active connection id??
    return connections


async def get_schema_list(controller):
    """
    Obtains list of existing schemas

    Parameters:
    -----------
    controller: AriesController
        The aries_cloudcontroller object

    Returns
    -------
    created_schemas : dict
        List of schemas
    """
    created_schemas = await controller.schema.get_created_schema()
    if not created_schemas:
        raise HTTPException(
            status_code=404, detail="Something went wrong. Could not obtain schema list"
        )
    return created_schemas


async def write_schema_definition(controller, schema_definition_request):
    """
    Writes schema definition to the ledger

    Parameters:
    -----------
    controller: AriesController
        The aries_cloudcontroller object

    schema_definition_request : Contains the schema name,schema version, schema attributes

    Returns:
    --------
    write_schema_resp : dict

    """
    write_schema_resp = await controller.schema.write_schema(
        schema_definition_request.schema_name,
        schema_definition_request.schema_attrs,
        schema_definition_request.schema_version,
    )

    if not write_schema_resp or write_schema_resp == {}:
        raise HTTPException(
            status_code=404,
            detail=f"Something went wrong.\n Could not write schema to ledger.\n{schema}",
        )
    return write_schema_resp


# Need to rename this?
async def verify_proof_req(controller, presentation_exchange_id):
    verify = await controller.proofs.verify_presentation(presentation_exchange_id)

    if not verify:
        raise HTTPException(
            status_code=404,
            detail="Something went wrong. Could not verify proof request",
        )

    return verify


async def send_proof_request(controller, proof_request_web_request):
    response = await controller.proofs.send_request(proof_request_web_request)

    if not response:
        raise HTTPException(
            status_code=404, detail="Something went wrong. Could not send proof request"
        )

    return response
