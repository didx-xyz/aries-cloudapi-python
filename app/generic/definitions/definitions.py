import asyncio
from typing import List, Optional

from aries_cloudcontroller import (
    AcaPyClient,
    CredentialDefinition as AcaPyCredentialDefinition,
    ModelSchema,
)
from aries_cloudcontroller.model.credential_definition_send_request import (
    CredentialDefinitionSendRequest,
)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.dependencies import agent_selector

router = APIRouter(
    prefix="/generic/definitions",
    tags=["definitions"],
)


class CreateCredentialDefinition(BaseModel):
    # Revocation not supported currently
    # support_revocation: bool = False
    tag: str = Field(..., example="default")
    schema_id: str = Field(..., example="CXQseFxV34pcb8vf32XhEa:2:test_schema:0.3")


class CredentialDefinition(BaseModel):
    id: str = Field(..., example="5Q1Zz9foMeAA8Q7mrmzCfZ:3:CL:7:default")
    tag: str = Field(..., example="default")
    schema_id: str = Field(..., example="CXQseFxV34pcb8vf32XhEa:2:test_schema:0.3")


class CredentialSchema(BaseModel):
    id: str = Field(..., example="CXQseFxV34pcb8vf32XhEa:2:test_schema:0.3")
    name: str = Field(..., example="test_schema")
    version: str = Field(..., example="0.3.0")
    attribute_names: List[str] = Field(..., example=["speed"])


def _credential_schema_from_acapy(schema: ModelSchema):
    return CredentialSchema(
        id=schema.id,
        name=schema.name,
        version=schema.version,
        attribute_names=schema.attr_names,
    )


def _credential_definition_from_acapy(credential_definition: AcaPyCredentialDefinition):
    return CredentialDefinition(
        id=credential_definition.id,
        tag=credential_definition.tag,
        schema_id=credential_definition.schema_id,
    )


@router.get("/credentials", response_model=List[CredentialDefinition])
async def get_credential_definitions(
    issuer_did: Optional[str] = None,
    credential_definition_id: Optional[str] = None,
    schema_id: Optional[str] = None,
    schema_issuer_did: Optional[str] = None,
    schema_name: Optional[str] = None,
    schema_version: Optional[str] = None,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Retrieve credential definitions the current agent created.

    Parameters:
    -----------
    issuer_did: str (Optional)\n
    credential_definition_id: str (Optional)\n
    schema_id: str (Optional)\n
    schema_issuer_id: str (Optional)\n
    schema_version: str (Optional)\n

    Returns:
    ---------
    The created credential definitions.
    """
    # Get all created credential definition ids that match the filter
    response = await aries_controller.credential_definition.get_created_cred_defs(
        issuer_did=issuer_did,
        cred_def_id=credential_definition_id,
        schema_id=schema_id,
        schema_issuer_did=schema_issuer_did,
        schema_name=schema_name,
        schema_version=schema_version,
    )

    # Initiate retrieving all credential definitions
    credential_definition_ids = response.credential_definition_ids or []
    get_credential_definition_futures = [
        aries_controller.credential_definition.get_cred_def(
            cred_def_id=credential_definition_id
        )
        for credential_definition_id in credential_definition_ids
    ]

    # Wait for completion of retrieval and transform all credential definitions into response model (if a credential definition was returned)
    credential_definition_results = await asyncio.gather(
        *get_credential_definition_futures
    )
    credential_definitions = [
        _credential_definition_from_acapy(credential_definition.credential_definition)
        for credential_definition in credential_definition_results
        if credential_definition.credential_definition
    ]

    return credential_definitions


@router.get(
    "/credentials/{credential_definition_id}", response_model=CredentialDefinition
)
async def get_credential_definition_by_id(
    credential_definition_id: str,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Get credential definition by id.

    Parameters:
    -----------
    credential_definition_id: str
        credential definition id

    """
    credential_definition = await aries_controller.credential_definition.get_cred_def(
        cred_def_id=credential_definition_id
    )

    if not credential_definition.credential_definition:
        raise HTTPException(
            404, f"Credential Definition with id {credential_definition_id} not found"
        )

    return _credential_definition_from_acapy(
        credential_definition.credential_definition
    )


@router.post("/")
async def create_credential_definition(
    credential_definition: CreateCredentialDefinition,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Create a credential definition.

    Parameters:
    -----------
    credential_definition: CreateCredentialDefinition
        Payload for creating a credential definition.

    Returns:
    --------
    Credential Definition
    """
    return await aries_controller.credential_definition.publish_cred_def(
        body=CredentialDefinitionSendRequest(
            schema_id=credential_definition.schema_id,
            # Revocation not supported yet
            support_revocation=False,
            tag=credential_definition.tag,
        )
    )


@router.get("/schemas", response_model=List[CredentialSchema])
async def get_schemas(
    schema_id: Optional[str] = None,
    schema_issuer_did: Optional[str] = None,
    schema_name: Optional[str] = None,
    schema_version: Optional[str] = None,
    aries_controller: AcaPyClient = Depends(agent_selector),
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
    # Get all created schema ids that match the filter
    response = await aries_controller.schema.get_created_schemas(
        schema_id=schema_id,
        schema_issuer_did=schema_issuer_did,
        schema_name=schema_name,
        schema_version=schema_version,
    )

    # Initiate retrieving all schemas
    schema_ids = response.schema_ids or []
    get_schema_futures = [
        aries_controller.schema.get_schema(schema_id=schema_id)
        for schema_id in schema_ids
    ]

    # Wait for completion of retrieval and transform all schemas into response model (if a schema was returned)
    schema_results = await asyncio.gather(*get_schema_futures)
    schemas = [
        _credential_schema_from_acapy(schema.schema_)
        for schema in schema_results
        if schema.schema_
    ]

    return schemas


@router.get("/schemas/{schema_id}", response_model=CredentialSchema)
async def get_schema(
    schema_id: str,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Retrieve schema by id.

    Parameters:
    -----------
    schema_id: str
        schema id
    """
    schema = await aries_controller.schema.get_schema(schema_id=schema_id)

    if not schema.schema_:
        raise HTTPException(404, f"Schema with id {schema_id} not found")

    return _credential_schema_from_acapy(schema.schema_)
