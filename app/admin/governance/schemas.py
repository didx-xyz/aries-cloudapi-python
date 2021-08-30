from typing import List, Optional

from aries_cloudcontroller import AriesAgentControllerBase
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from dependencies import yoma_agent

router = APIRouter(prefix="/admin/governance/schemas", tags=["admin: schemas"])


class SchemaDefinition(BaseModel):
    name: str
    version: str
    attributes: List[str]


@router.get("/{schema_id}")
async def get_schema(
    schema_id: str,
    aries_controller: AriesAgentControllerBase = Depends(yoma_agent),
):
    """
    Retrieve schemas by id.

    Parameters:
    -----------
    schema_id: str
        schema id
    """
    return await aries_controller.schema.get_by_id(schema_id=schema_id)


@router.get("/")
async def get_schemas(
    schema_id: Optional[str] = None,
    schema_issuer_did: Optional[str] = None,
    schema_name: Optional[str] = None,
    schema_version: Optional[str] = None,
    aries_controller: AriesAgentControllerBase = Depends(yoma_agent),
):
    """
    Retrieve schemas that the current agent created.

    Parameters:
    -----------
    schema_id: str (Optional)
    schema_issuer_did: str (Optional)
    schema_name: str (Optional)
    schema_version: str (Optional)

    Returns:
    --------
    Json response with created schemas from ledger.
    """
    return await aries_controller.schema.get_created_schema(
        schema_id=schema_id,
        schema_issuer_did=schema_issuer_did,
        schema_name=schema_name,
        schema_version=schema_version,
    )


@router.post("/")
async def create_schema(
    schema_definition: SchemaDefinition,
    aries_controller: AriesAgentControllerBase = Depends(yoma_agent),
):
    """
    Create a new schema.

    Parameters:
    ------------
    schema_definition: SchemaDefinition
        Payload for creating a schema.

    Returns:
    --------
    The response object from creating a schema.
    """
    schema_definition = await aries_controller.schema.write_schema(
        schema_definition.name, schema_definition.attributes, schema_definition.version
    )
    return schema_definition


@router.post("/update")
async def update_schema(
    schema_id: str,
    schema_definition: SchemaDefinition,
    aries_controller: AriesAgentControllerBase = Depends(yoma_agent),
):
    """
    Update an existing schema. This is a convenience method to mimic updating a schema.
    Technically a new schema will be created under the same name with a new version and its own hash.

    Parameters:
    -----------
    schema_id: str
        The schema ID
    schema_definition: SchemaDefinition
        Payload for creating a schema.

    Returns:
    --------
    The response object from creating a schema.
    """

    schema_def = await aries_controller.schema.get_by_id(schema_id=schema_id)
    assert schema_def["schema"]
    try:
        assert float(schema_def["schema"]["version"]) < float(schema_definition.version)
    except AssertionError:
        raise HTTPException(
            status_code=405,
            detail="Updated version must be higher than previous version",
        )
    schema_definition = await aries_controller.schema.write_schema(
        schema_definition.name, schema_definition.attributes, schema_definition.version
    )
    return schema_definition


@router.get("/list/")
async def get_schemas_list_detailed(
    schema_id: Optional[str] = None,
    schema_issuer_did: Optional[str] = None,
    schema_name: Optional[str] = None,
    schema_version: Optional[str] = None,
    aries_controller: AriesAgentControllerBase = Depends(yoma_agent),
):
    """
    Retrieve a list of schemas from the registry and dispaly them in human-readable and friendly form.

    Parameters:
    -----------
    schema_id: str (Optional)
    schema_issuer_did: str (Optional)
    schema_name: str (Optional)
    schema_version: str (Optional)

    Returns:
    --------
    JSON object by ID with name, version ,and attributes by schema.
    """
    ids = (
        await aries_controller.schema.get_created_schema(
            schema_id=schema_id,
            schema_issuer_did=schema_issuer_did,
            schema_name=schema_name,
            schema_version=schema_version,
        )
    )["schema_ids"]
    schemas = {}
    for id in ids:
        schema = (await aries_controller.schema.get_by_id(schema_id=id))["schema"]
        schemas[schema["id"]] = {
            "name": schema["name"],
            "version": schema["version"],
            "attributes": schema["attrNames"],
        }
    return schemas
