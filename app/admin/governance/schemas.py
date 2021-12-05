from typing import List, Optional

from aries_cloudcontroller import (
    AcaPyClient,
    SchemaGetResult,
    SchemasCreatedResult,
    SchemaSendRequest,
    SchemaSendResult,
)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import agent_role, Role

router = APIRouter(prefix="/admin/governance/schemas", tags=["admin: schemas"])


class SchemaDefinition(BaseModel):
    name: str
    version: str
    attributes: List[str]


@router.get("/{schema_id}", response_model=SchemaGetResult)
async def get_schema(
    schema_id: str,
    aries_controller: AcaPyClient = Depends(agent_role(Role.YOMA)),
):
    """
    Retrieve schemas by id.

    Parameters:
    -----------
    schema_id: str
        schema id
    """
    return await aries_controller.schema.get_schema(schema_id=schema_id)


@router.get("/", response_model=SchemasCreatedResult)
async def get_schemas(
    schema_id: Optional[str] = None,
    schema_issuer_did: Optional[str] = None,
    schema_name: Optional[str] = None,
    schema_version: Optional[str] = None,
    aries_controller: AcaPyClient = Depends(agent_role(Role.YOMA)),
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
    return await aries_controller.schema.get_created_schemas(
        schema_id=schema_id,
        schema_issuer_did=schema_issuer_did,
        schema_name=schema_name,
        schema_version=schema_version,
    )


@router.post("/", response_model=SchemaSendResult)
async def create_schema(
    schema_definition: SchemaDefinition,
    aries_controller: AcaPyClient = Depends(agent_role(Role.YOMA)),
) -> SchemaSendResult:
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
    schema_send_request = SchemaSendRequest(
        attributes=schema_definition.attributes,
        schema_name=schema_definition.name,
        schema_version=schema_definition.version,
    )
    result = await aries_controller.schema.publish_schema(body=schema_send_request)
    return result


@router.post("/update", response_model=SchemaSendResult)
async def update_schema(
    schema_id: str,
    schema_definition: SchemaDefinition,
    aries_controller: AcaPyClient = Depends(agent_role(Role.YOMA)),
) -> SchemaSendResult:
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

    response = await aries_controller.schema.get_schema(schema_id=schema_id)

    schema = response.schema_

    if not schema or not schema.version or not schema.attr_names:
        raise HTTPException(404, f"Schema {schema_id} not found")

    try:
        assert float(schema.version) < float(schema_definition.version)
    except AssertionError:
        raise HTTPException(
            status_code=405,
            detail="Updated version must be higher than previous version",
        )
    schema_send_request = SchemaSendRequest(
        attributes=schema_definition.attributes,
        schema_name=schema_definition.name,
        schema_version=schema_definition.version,
    )

    response = await aries_controller.schema.publish_schema(body=schema_send_request)
    return response


@router.get("/list/")
async def get_schemas_list_detailed(
    schema_id: Optional[str] = None,
    schema_issuer_did: Optional[str] = None,
    schema_name: Optional[str] = None,
    schema_version: Optional[str] = None,
    aries_controller: AcaPyClient = Depends(agent_role(Role.YOMA)),
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
        await aries_controller.schema.get_created_schemas(
            schema_id=schema_id,
            schema_issuer_did=schema_issuer_did,
            schema_name=schema_name,
            schema_version=schema_version,
        )
    ).dict()["schema_ids"]
    schemas = {}
    for id in ids:
        schema = (await aries_controller.schema.get_schema(schema_id=id)).dict()[
            "schema_"
        ]
        schemas[schema["id"]] = {
            "name": schema["name"],
            "version": schema["version"],
            "attributes": schema["attr_names"],
        }
    return schemas
