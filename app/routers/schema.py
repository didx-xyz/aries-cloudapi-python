import logging
from distutils.util import strtobool
from typing import List
import os

from fastapi import APIRouter, HTTPException, Query
import aries_cloudcontroller

from schemas import SchemaLedgerRequest, SchemaResponse

logger = logging.getLogger(__name__)

router = APIRouter()

admin_url = os.getenv("ACAPY_ADMIN_URL")
admin_port = os.getenv("ACAPY_ADMIN_PORT")
admin_api_key = os.getenv("ACAPY_ADMIN_API_KEY")
is_multitenant = strtobool(os.getenv("IS_MULTITENANT", "True"))

ledger_url = os.getenv("LEDGER_NETWORK_URL")


@router.get("/schema/all_schemas", tags=["schemas"])
async def get_schema():
    """
    Get all valid schemas from YOMA
    """
    try:
        aries_agent_controller = aries_cloudcontroller.AriesAgentController(
            admin_url=f"{admin_url}:{admin_port}",
            api_key=admin_api_key,
            is_multitenant=is_multitenant,
        )
        created_schemas = await aries_agent_controller.schema.get_created_schema()
        await aries_agent_controller.terminate()
        return created_schemas

    except Exception as e:
        await aries_agent_controller.terminate()
        raise HTTPException(
            status_code=500,
            detail=f"Something went wrong.\n Could not get schema from ledger.\n{e}.",
        ) from e


@router.post(
    "/schema/write-schema-and-credential-definition",
    tags=["schemas", "credentials"],
    response_model=SchemaResponse,
)
async def write_credential_schema(
    schema_name: str, schema_version: str, schema_attrs: List[str] = Query(None)
):
    """
    Create schema and credential definition and
    write it to the ledger.

    Parameters:
    ----------
    * schema_name: str
        The name of the schema to be defined
    * schema_version: str
        The version of the schema to be written\n
        Should be of the form x.x.x where x is an integer
    * schema_attributes: list, optional
        A list of attributes for the schema (default is None)

    Returns:
    --------
    as json:
    * schema
    * schema_id
    * credential_definition
    * credential_id
    """
    try:
        aries_agent_controller = aries_cloudcontroller.AriesAgentController(
            admin_url=f"{admin_url}:{admin_port}",
            api_key=admin_api_key,
            is_multitenant=is_multitenant,
        )

        # Defining schema and writing it to the ledger

        schema_definition_request = SchemaLedgerRequest(
            schema_name=schema_name,
            schema_version=schema_version,
            schema_attrs=schema_attrs,
        )

        write_schema_resp = await aries_agent_controller.schema.write_schema(
            schema_definition_request.schema_name,
            schema_definition_request.schema_attrs,
            schema_definition_request.schema_version,
        )

        if not write_schema_resp or write_schema_resp == {}:
            await aries_agent_controller.terminate()
            raise HTTPException(
                status_code=404,
                detail=f"Something went wrong.\n Could not write schema to ledger.\n{schema}",
            )
        schema_id = write_schema_resp["schema_id"]

        # Writing credential definition
        credential_definition = await aries_agent_controller.definitions.write_cred_def(
            schema_id
        )
        if not credential_definition:
            await aries_agent_controller.terminate()
            raise HTTPException(
                status_code=404,
                detail=f"Something went wrong.\nCould not write credential definition to ledger.\n{credential_definition}",
            )
        credential_definition_id = credential_definition["credential_definition_id"]

        final_response = SchemaResponse(
            schema_resp=write_schema_resp,
            schema_id=schema_id,
            credential_definition=credential_definition,
            credential_id=credential_definition_id,
        )
        await aries_agent_controller.terminate()
        return final_response
    except Exception as e:
        await aries_agent_controller.terminate()
        logger.error(f"{e!r}")
        raise HTTPException(
            status_code=500,
            detail=f"Something went wrong: {e!r}",
        ) from e


@router.get("/schema/registry", tags=["schemas", "registry"])
async def get_schema_registry():
    """
    A function to obtain all schemas written to the ledger by YOMA
    and YOMA only.

    Returns:
    --------
    schemas: [dict]
        A list of schema definitions
    """
    aries_agent_controller = aries_cloudcontroller.AriesAgentController(
        admin_url=f"{admin_url}:{admin_port}",
        api_key=admin_api_key,
        is_multitenant=is_multitenant,
    )

    schemas = {}
    # schemas = aries_agent_controller.schema

    await aries_agent_controller.terminate()
    return schemas
