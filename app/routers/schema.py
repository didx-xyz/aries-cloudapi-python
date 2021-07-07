import logging
import os
import traceback
from distutils.util import strtobool
from typing import List

from dependencies import *
from facade import (
    get_schema_list,
    write_credential_def,
    write_schema_definition,
)
from fastapi import APIRouter, Query, Depends
from schemas import SchemaLedgerRequest, SchemaResponse
from aries_cloudcontroller import AriesAgentControllerBase

router = APIRouter(prefix="/schemas", tags=["schemas"])

logger = logging.getLogger(__name__)

admin_url = os.getenv("ACAPY_ADMIN_URL")
admin_port = os.getenv("ACAPY_ADMIN_PORT")
admin_api_key = os.getenv("ACAPY_ADMIN_API_KEY")
is_multitenant = strtobool(os.getenv("IS_MULTITENANT", "True"))
ledger_url = os.getenv("LEDGER_NETWORK_URL")


@router.get("/all_schemas")
async def get_schema(
    aries_controller: AriesAgentControllerBase = Depends(yoma_agent),
):
    """
    Get all valid schemas from YOMA

    Parameters:
    -----------
    api_key: Header(None)
        The request header object api_key
    wallet_id: Header(None)
        The request header object wallet_id
    tenant_jwt: Header(None)
        The request header object tenant_jwt

    Returns:
    --------
    created_schema: dict
        The created schema response in JSON
    """
    try:
        # async with create_controller(auth_headers) as controller:
        # TODO: Should this come from env var or from the client request?
        created_schemas = await get_schema_list(aries_controller)

        return created_schemas

    except Exception as e:
        err_trace = traceback.print_exc()
        logger.error(
            f"Failed to retrieve schema list.The following error occured:\n{e!r}\n{err_trace}"
        )
        raise e


@router.post(
    "/write-schema-and-credential-definition",
    tags=["credentials"],
    response_model=SchemaResponse,
)
async def write_credential_schema(
    schema_name: str,
    schema_version: str,
    schema_attrs: List[str] = Query(None),
    aries_controller: AriesAgentControllerBase = Depends(yoma_agent),
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
    api_key: Header(None)
        The request header object api_key
    wallet_id: Header(None)
        The request header object wallet_id
    tenant_jwt: Header(None)
        The request header object tenant_jwt

    Returns:
    --------
    as json:
    * schema
    * schema_id
    * credential_definition
    * credential_id
    """
    try:
        # TODO: Should this come from env var or from the client request?

        # Defining schema and writing it to the ledger
        schema_definition_request = SchemaLedgerRequest(
            schema_name=schema_name,
            schema_version=schema_version,
            schema_attrs=schema_attrs,
        )

        write_schema_resp = await write_schema_definition(
            aries_controller, schema_definition_request
        )

        schema_id = write_schema_resp["schema_id"]

        # Writing credential definition
        credential_definition = await write_credential_def(aries_controller, schema_id)

        credential_definition_id = credential_definition["credential_definition_id"]

        final_response = SchemaResponse(
            schema_resp=write_schema_resp,
            schema_id=schema_id,
            credential_definition=credential_definition,
            credential_definition_id=credential_definition_id,
        )
        return final_response
    except Exception as e:
        err_trace = traceback.print_exc()
        logger.error(
            f"Something went wrong, the following error occured:{e!r}\n{err_trace}"
        )
        raise e
