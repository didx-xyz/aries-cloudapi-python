from typing import List, Optional

from aries_cloudcontroller import (
    AcaPyClient,
    SchemaGetResult,
    SchemasCreatedResult,
    SchemaSendRequest,
    SchemaSendResult,
)
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.facades import trust_registry

from app.dependencies import agent_role, Role

router = APIRouter(prefix="/admin/governance/schemas", tags=["admin: schemas"])

governance_role = Depends(agent_role(Role.GOVERNANCE))


class SchemaDefinition(BaseModel):
    name: str
    version: str
    attributes: List[str]


class UpdateSchema(BaseModel):
    version: str
    attributes: List[str]


@router.get("/{schema_id}", response_model=SchemaGetResult)
async def get_schema(schema_id: str, aries_controller: AcaPyClient = governance_role):
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
    aries_controller: AcaPyClient = governance_role,
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
    schema_definition: SchemaDefinition, aries_controller: AcaPyClient = governance_role
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

    # Register the schema in the trust registry
    try:
        await trust_registry.register_schema(schema_id=result.schema_id)
    except trust_registry.TrustRegistryException as error:
        # If status_code is 405 it means the schema already exists in the trust registry
        # That's okay, because we've achieved our intended result:
        #   make sure the schema is registered in the trust registry
        if error.status_code != 405:
            raise error

    return result
