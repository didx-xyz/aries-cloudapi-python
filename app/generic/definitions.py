import asyncio
import json
from typing import List, Optional

from aries_cloudcontroller import (
    AcaPyClient,
    CredentialDefinition as AcaPyCredentialDefinition,
    ModelSchema,
    SchemaSendRequest,
    SchemaSendResult,
    TxnOrCredentialDefinitionSendResult,
)
from app.error.cloud_api_error import CloudApiException
from aries_cloudcontroller.model.credential_definition_send_request import (
    CredentialDefinitionSendRequest,
)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.dependencies import (
    AcaPyAuthVerified,
    acapy_auth_verified,
    agent_role,
    agent_selector,
)
from app.role import Role
from app.facades import trust_registry, acapy_wallet
from app.webhook_listener import start_listener

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


class CreateSchema(BaseModel):
    name: str = Field(..., example="test_schema")
    version: str = Field(..., example="0.3.0")
    attribute_names: List[str] = Field(..., example=["speed"])


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

    cloudapi_credential_definition = _credential_definition_from_acapy(
        credential_definition.credential_definition
    )

    # We need to update the schema_id on the returned credential definition as
    # ACA-Py returns the schema_id as the seq_no
    schema = await get_schema(
        schema_id=cloudapi_credential_definition.schema_id,
        aries_controller=aries_controller,
    )
    cloudapi_credential_definition.schema_id = schema.id

    return cloudapi_credential_definition


@router.post("/credentials", response_model=CredentialDefinition)
async def create_credential_definition(
    credential_definition: CreateCredentialDefinition,
    # Only Yoma and ecosystem issuers can create credential definitions. Further validation
    # done inside the endpoint implementation.
    aries_controller: AcaPyClient = Depends(agent_role([Role.YOMA, Role.ECOSYSTEM])),
    auth: AcaPyAuthVerified = Depends(acapy_auth_verified),
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

    # Assert the agent has a public did
    public_did = await acapy_wallet.assert_public_did(aries_controller)

    # Make sure we are allowed to issue this schema according to trust registry rules
    await trust_registry.assert_valid_issuer(
        public_did, credential_definition.schema_id
    )

    wait_for_event, stop_listener = await start_listener(
        topic="endorsements", wallet_id=auth.wallet_id
    )

    result = await aries_controller.credential_definition.publish_cred_def(
        body=CredentialDefinitionSendRequest(
            schema_id=credential_definition.schema_id,
            # Revocation not supported yet
            support_revocation=False,
            tag=credential_definition.tag,
        )
    )

    if isinstance(result, TxnOrCredentialDefinitionSendResult):
        try:
            # Wait for transaction to be acknowledged and written to the ledger
            await wait_for_event(
                filter_map={
                    "state": "transaction_acked",
                    "transaction_id": result.txn.transaction_id,
                },
                timeout=300,
            )
        except asyncio.TimeoutError:
            raise CloudApiException(
                "Timeout waiting for endorser to accept the endorsement request"
            )

        try:
            transaction = await aries_controller.endorse_transaction.get_transaction(
                tran_id=result.txn.transaction_id
            )

            # Based on
            # https://github.com/bcgov/traction/blob/6c86d35f3e8b8ca0b88a198876155ba820fb34ea/services/traction/api/services/SchemaWorkflow.py#L276-L280
            signatures = transaction.signature_response[0]["signature"]
            endorser_public_did = list(signatures.keys())[0]
            signature = json.loads(signatures[endorser_public_did])

            public_did = signature["identifier"]
            sig_type = signature["operation"]["signature_type"]
            schema_ref = signature["operation"]["ref"]
            tag = signature["operation"]["tag"]
            credential_definition_id = f"{public_did}:3:{sig_type}:{schema_ref}:{tag}"
        except Exception as e:
            raise CloudApiException(
                "Unable to construct credential definition id from signature response"
            ) from e

        # FIXME: ACA-Py 0.7.3 has no way to associate the credential definition id with a transaction record
        # This methods find the created credential definition for a schema and tag (which is always unique)
        # credential_definition_id = (
        #     await get_credential_definition_id_for_schema_and_tag(
        #         aries_controller,
        #         credential_definition.schema_id,
        #         credential_definition.tag,
        #     )
        # )
        # if not credential_definition_id:
        #     raise CloudApiException(
        #         f"Could not find any created credential definitions for schema_id {credential_definition.schema_id} and tag {credential_definition.tag}",
        #         500,
        #     )

    else:
        await stop_listener()
        credential_definition_id = result.credential_definition_id

    # ACA-Py only returns the id after creating a credential definition
    # We want consistent return types across all endpoints, so retrieving the credential
    # definition here.
    return await get_credential_definition_by_id(
        credential_definition_id, aries_controller
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


@router.post("/", response_model=CredentialSchema)
async def create_schema(
    schema: CreateSchema,
    # Only yoma can create schemas
    aries_controller: AcaPyClient = Depends(agent_role(Role.YOMA)),
) -> CredentialSchema:
    """
    Create a new schema.

    Parameters:
    ------------
    schema: CreateSchema
        Payload for creating a schema.

    Returns:
    --------
    The response object from creating a schema.
    """
    schema_send_request = SchemaSendRequest(
        attributes=schema.attribute_names,
        schema_name=schema.name,
        schema_version=schema.version,
    )
    result = await aries_controller.schema.publish_schema(
        body=schema_send_request, create_transaction_for_endorser=False
    )

    if not isinstance(result, SchemaSendResult) or not result.schema_:
        raise CloudApiException("Error creating schema", 500)

    # Register the schema in the trust registry
    try:
        await trust_registry.register_schema(schema_id=result.schema_id)
    except trust_registry.TrustRegistryException as error:
        # If status_code is 405 it means the schema already exists in the trust registry
        # That's okay, because we've achieved our intended result:
        #   make sure the schema is registered in the trust registry
        if error.status_code != 405:
            raise error

    return _credential_schema_from_acapy(result.schema_)
