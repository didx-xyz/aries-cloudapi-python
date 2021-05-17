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

@router.get("/schema/write-schema-and-credential-definition", tags=["schema" , "credential"])
async def  credential_schema():
    """
    Create Schema and credential definition and
    write it to the ledger.
    """


    #Defining schema and writing it to the ledger
    schema_name = "yoma_test_schema"
    schema_version = "0.01"
    schema_attributes = ["name", "age","skill", "DOB"]

    schema = await aries_agent_controller.schema.write_schema(schema_name, schema_attributes, schema_version)
    schema_id = response["schema_id"]

    #Writing credential definition
    credential_definition = await aries_agent_controller.definitions.write_cred_def(schema_id)
    credential_definition_id = response["credential_definition_id"]


    final_response = {
        "schema" : schema,
        "schema_id" : schema_id,
        "credential" : credential_definition,
        "credential_id" : credential_definition_id
    }
    return final_response
