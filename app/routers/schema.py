from fastapi import APIRouter, HTTPException
import requests
import json

import aries_cloudcontroller

router = APIRouter()


aries_agent_controller = aries_cloudcontroller.AriesAgentController(
    admin_url=f"http://multitenant-agent:3021",
    api_key="adminApiKey",
    is_multitenant=True,
)


@router.post("/schema/schema_definition", tags=["schema", "credential"])
async def schema_define():
    """
    Define Schema
    """
    pass


@router.get(
    "/schema/write-schema-and-credential-definition", tags=["schema", "credential"]
)
async def write_credential_schema(
    schema_name: str, schema_version: str, schema_attrs: list
):
    """
    Create schema and credential definition and
    write it to the ledger.

    Parameters:
    ----------
    * schema_name: str
        The name of the schema to be defined
    * schema_version: str
        The version of the schema to be written
    * schema_attributes: list, optional
        A list of attributes for the schema (default is None)

    Returns:
    --------
    * schema
    * schema_id
    * credential_definition
    * credential_id
    """

    # Defining schema and writing it to the ledger
    schema_name = schema_name
    schema_version = schema_version
    schema_attributes = schema_attrs

    write_schema_resp = await aries_agent_controller.schema.write_schema(
        schema_name, schema_attributes, schema_version
    )
    if not write_schema_resp or write_schema_resp == {}:
        raise HTTPException(
            status_code=418,
            detail=f"Something went wrong.\n Could not write schema to ledger.\n{schema}",
        )
    schema_id = write_schema_resp["schema_id"]

    # Writing credential definition
    credential_definition = await aries_agent_controller.definitions.write_cred_def(
        schema_id
    )
    if not credential_definition:
        raise HTTPException(
            status_code=418,
            detail=f"Something went wrong.\nCould not write credential definition to ledger.\n{credential_definition}",
        )
    credential_definition_id = credential_definition["credential_definition_id"]

    final_response = {
        "schema": schema,
        "schema_id": schema_id,
        "credential": credential_definition,
        "credential_id": credential_definition_id,
    }
    return final_response
