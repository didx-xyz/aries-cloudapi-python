from typing import List, Optional

from aries_cloudcontroller import SchemaSendRequest
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies.acapy_clients import client_from_auth, get_governance_controller
from app.dependencies.auth import (
    AcaPyAuth,
    AcaPyAuthVerified,
    acapy_auth_from_header,
    acapy_auth_governance,
    acapy_auth_verified,
)
from app.dependencies.role import Role
from app.exceptions import handle_acapy_call, handle_model_with_validation
from app.models.definitions import (
    CreateCredentialDefinition,
    CreateSchema,
    CredentialDefinition,
    CredentialSchema,
)
from app.services.definitions import (
    create_cred_def,
    create_schema_service,
    get_cred_defs,
    get_schemas_governance,
    get_schemas_tenant,
)
from app.util.definitions import (
    credential_definition_from_acapy,
    credential_schema_from_acapy,
)
from app.util.retry_method import coroutine_with_retry
from shared.log_config import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/v1/definitions",
    tags=["definitions"],
)


@router.post("/schemas", summary="Create a new Schema", response_model=CredentialSchema)
async def create_schema(
    schema: CreateSchema,
    # Only governance can create schemas
    governance_auth: AcaPyAuthVerified = Depends(acapy_auth_governance),
) -> CredentialSchema:
    """
    Create and publish a new schema to the ledger
    ---
    **NB**: Only governance can create schemas.

    A schema is used to create credential definitions, which is used for issuing credentials.
    The schema defines the attributes that can exist in that credential.

    When a schema is created, it is published to the ledger and written to our public trust registry,
    so that everyone in the ecosystem can view schemas that are valid and available.

    Request Body:
    ---
        body: CreateSchema
            name: str
                The name of the schema.
            version: str
                The version of the schema.
            attribute_names: List[str]
                The attribute names of the schema.

    Returns:
    ---
        CredentialSchema
            The created schema object
    """
    bound_logger = logger.bind(body=schema)
    bound_logger.info("POST request received: Create schema (publish and register)")

    schema_send_request = handle_model_with_validation(
        logger=bound_logger,
        model_class=SchemaSendRequest,
        attributes=schema.attribute_names,
        schema_name=schema.name,
        schema_version=schema.version,
    )
    async with get_governance_controller(governance_auth) as aries_controller:
        schema_response = await create_schema_service(
            logger=bound_logger,
            aries_controller=aries_controller,
            schema_request=schema_send_request,
            schema=schema,
        )
    return schema_response


@router.get(
    "/schemas",
    summary="Get Created Schemas",
    response_model=List[CredentialSchema],
)
async def get_schemas(
    schema_id: Optional[str] = None,
    schema_issuer_did: Optional[str] = None,
    schema_name: Optional[str] = None,
    schema_version: Optional[str] = None,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> List[CredentialSchema]:
    """
    Get created schemas
    ---
    All tenants can call this endpoint to view available schemas.

    If governance calls this endpoint, it will return all the schemas created by governance
    (whether the schemas are on the trust registry or not).

    If tenants call this endpoint, it will return all schemas on the trust registry.
    The difference between this endpoint and the public trust registry endpoint, is that this response includes
    the attribute information of the schemas.

    Results can be filtered by the parameters listed below.

    Parameters (Optional):
    ---
        schema_id: str
        schema_issuer_did: str
        schema_name: str
        schema_version: str

    Returns:
    ---
        List[CredentialSchema]
            A list of created schemas
    """
    is_governance = auth.role == Role.GOVERNANCE
    bound_logger = logger.bind(
        body={
            "is_governance": is_governance,
            "schema_id": schema_id,
            "schema_issuer_did": schema_issuer_did,
            "schema_name": schema_name,
            "schema_version": schema_version,
        }
    )

    async with client_from_auth(auth) as aries_controller:
        if not is_governance:  # regular tenant is calling endpoint
            schemas = await get_schemas_tenant(
                logger=bound_logger,
                aries_controller=aries_controller,
                schema_id=schema_id,
                schema_issuer_did=schema_issuer_did,
                schema_name=schema_name,
                schema_version=schema_version,
            )

        else:  # Governance is calling the endpoint
            schemas = await get_schemas_governance(
                logger=bound_logger,
                aries_controller=aries_controller,
                schema_id=schema_id,
                schema_issuer_did=schema_issuer_did,
                schema_name=schema_name,
                schema_version=schema_version,
            )

    if schemas:
        bound_logger.info("Successfully fetched schemas.")
    else:
        bound_logger.info("No schemas matching request.")

    return schemas


@router.get(
    "/schemas/{schema_id}",
    summary="Get a Schema",
    response_model=CredentialSchema,
)
async def get_schema(
    schema_id: str,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> CredentialSchema:
    """
    Retrieve schema by id
    ---
    This endpoint fetches a schema from the ledger, using the schema_id.

    Any tenant can call this endpoint to retrieve a schema.
    This endpoint will list all the attributes of the schema.

    Parameters:
    ---
        schema_id: str
            schema id

    Returns:
    ---
        CredentialSchema
            The schema object
    """
    bound_logger = logger.bind(body={"schema_id": schema_id})
    bound_logger.info("GET request received: Get schema by id")

    async with client_from_auth(auth) as aries_controller:
        schema = await handle_acapy_call(
            logger=bound_logger,
            acapy_call=aries_controller.schema.get_schema,
            schema_id=schema_id,
        )

    if not schema.var_schema:
        bound_logger.info("Bad request: schema id not found.")
        raise HTTPException(404, f"Schema with id {schema_id} not found.")

    result = credential_schema_from_acapy(schema.var_schema)
    bound_logger.info("Successfully fetched schema by id.")
    return result


@router.post(
    "/credentials",
    summary="Create a new Credential Definition",
    response_model=CredentialDefinition,
)
async def create_credential_definition(
    credential_definition: CreateCredentialDefinition,
    auth: AcaPyAuthVerified = Depends(acapy_auth_verified),
) -> CredentialDefinition:
    """
    Create a credential definition
    ---
    Only issuers can create credential definitions.

    A credential definition essentially builds off a schema, which defines the attributes that can belong to a
    credential, and it specifies whether credentials using this definition are revocable or not.

    **NB**: If revocation is requested (`"support_revocation": true`), then revocation registries will be created.
    The creation of these revocation registries can take up to one minute.

    Request Body:
    ---
        body: CreateCredentialDefinition
            schema_id: str
                The id of the schema to use for this credential definition.
            tag: str
                The label to use for the credential definition.
            support_revocation: bool
                Whether you want credentials using this definition to be revocable or not

    Returns:
    ---
        CredentialDefinition
            The created credential definition
    """
    bound_logger = logger.bind(
        body={
            "schema_id": credential_definition.schema_id,
            "tag": credential_definition.tag,
            "support_revocation": credential_definition.support_revocation,
        }
    )
    bound_logger.info("POST request received: Create credential definition")

    support_revocation = credential_definition.support_revocation

    async with client_from_auth(auth) as aries_controller:
        # Assert the agent has a public did
        bound_logger.debug("Asserting client has public DID")
        try:
            public_did = await acapy_wallet.assert_public_did(aries_controller)
        except CloudApiException as e:
            log_message = f"Asserting public DID failed: {e}"

            if e.status_code == 403:
                bound_logger.info(log_message)
                client_error_message = (
                    "Wallet making this request has no public DID. "
                    "Only issuers with a public DID can make this request."
                )
            else:
                bound_logger.error(log_message)
                client_error_message = (
                    "Something went wrong while asserting if request is from a valid issuer. "
                    "Please try again."
                )

            raise CloudApiException(client_error_message, e.status_code) from e

        # Make sure we are allowed to issue this schema according to trust registry rules
        bound_logger.debug("Asserting client is a valid issuer")
        await assert_valid_issuer(public_did, credential_definition.schema_id)

        if support_revocation:
            endorser_connection = await handle_acapy_call(
                logger=bound_logger,
                acapy_call=aries_controller.connection.get_connections,
                alias=ACAPY_ENDORSER_ALIAS,
            )
            has_connections = len(endorser_connection.results) > 0

            if not has_connections:
                bound_logger.error(
                    "Failed to create credential definition supporting revocation: no endorser connection found. "
                    "Issuer attempted to create a credential definition with support for revocation but does not "
                    "have an active connection with an endorser, which is required for this operation."
                )

                raise CloudApiException(
                    "Credential definition creation failed: An active endorser connection is required "
                    "to support revocation. Please establish a connection with an endorser and try again."
                )

        bound_logger.debug("Publishing credential definition")
        request_body = handle_model_with_validation(
            logger=bound_logger,
            model_class=CredentialDefinitionSendRequest,
            schema_id=credential_definition.schema_id,
            support_revocation=support_revocation,
            tag=credential_definition.tag,
            revocation_registry_size=32767,
        )
        try:
            result = await handle_acapy_call(
                logger=bound_logger,
                acapy_call=aries_controller.credential_definition.publish_cred_def,
                body=request_body,
            )
            credential_definition_id = result.sent.credential_definition_id
        except CloudApiException as e:
            bound_logger.warning(
                "An Exception was caught while publishing credential definition: `{}` `{}`",
                e.detail,
                e.status_code,
            )
            if "already exists" in e.detail:
                raise CloudApiException(status_code=409, detail=e.detail) from e
            else:
                raise CloudApiException(
                    detail=f"Error while creating credential definition: {e.detail}",
                    status_code=e.status_code,
                ) from e

        # Wait for cred_def transaction to be acknowledged
        if result.txn and result.txn.transaction_id:
            bound_logger.debug(
                "The publish credential definition response provides a transaction id. "
                "Waiting for transaction to be in state `transaction_acked`"
            )

            try:
                # Wait for transaction to be acknowledged and written to the ledger
                await coroutine_with_retry_until_value(
                    coroutine_func=aries_controller.endorse_transaction.get_transaction,
                    args=(result.txn.transaction_id,),
                    field_name="state",
                    expected_value="transaction_acked",
                    logger=bound_logger,
                    max_attempts=10,
                    retry_delay=2,
                )
            except asyncio.TimeoutError as e:
                raise CloudApiException(
                    "Timeout waiting for endorser to accept the endorsement request.",
                    504,
                ) from e

            bound_logger.debug("Transaction has been acknowledged by the endorser")

        # Wait for revocation registry creation
        if support_revocation:
            try:
                bound_logger.debug("Waiting for revocation registry creation")
                await asyncio.wait_for(
                    wait_for_active_registry(
                        aries_controller, credential_definition_id
                    ),
                    timeout=REGISTRY_CREATION_TIMEOUT,
                )
            except asyncio.TimeoutError as e:
                bound_logger.error("Timeout waiting for revocation registry creation.")
                raise CloudApiException(
                    "Timeout waiting for revocation registry creation.",
                    504,
                ) from e

    # ACA-Py only returns the id after creating a credential definition
    # We want consistent return types across all endpoints, so retrieving the credential
    # definition here.

    # Retry logic to avoid race condition, as it can return 404
    result = await coroutine_with_retry(
        coroutine_func=get_credential_definition_by_id,
        args=(credential_definition_id, auth),
        logger=bound_logger,
        max_attempts=3,
        retry_delay=0.5,
    )
    bound_logger.info("Successfully created credential definition.")
    return result


@router.get(
    "/credentials",
    summary="Get Created Credential Definitions",
    response_model=List[CredentialDefinition],
)
async def get_credential_definitions(
    issuer_did: Optional[str] = None,
    credential_definition_id: Optional[str] = None,
    schema_id: Optional[str] = None,
    schema_issuer_did: Optional[str] = None,
    schema_name: Optional[str] = None,
    schema_version: Optional[str] = None,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> List[CredentialDefinition]:
    """
    Get credential definitions created by the tenant
    ---
    This endpoint returns all credential definitions created by the tenant. Only issuers can create
    credential definitions, and so only issuers will get results from this endpoint.

    The results can be filtered by the parameters listed below.

    Parameters (Optional):
    ---
        issuer_did: str
        credential_definition_id: str
        schema_id: str
        schema_issuer_id: str
        schema_version: str

    Returns:
    ---
        List[CredentialDefinition]
            A list of created credential definitions
    """
    bound_logger = logger.bind(
        body={
            "issuer_did": issuer_did,
            "credential_definition_id": credential_definition_id,
            "schema_id": schema_id,
            "schema_issuer_did": schema_issuer_did,
            "schema_name": schema_name,
            "schema_version": schema_version,
        }
    )
    bound_logger.info(
        "GET request received: Get credential definitions created by agent"
    )

    # Get all created credential definition ids that match the filter
    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Getting created credential definitions")
        response = await handle_acapy_call(
            logger=bound_logger,
            acapy_call=aries_controller.credential_definition.get_created_cred_defs,
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
            handle_acapy_call(
                logger=bound_logger,
                acapy_call=aries_controller.credential_definition.get_cred_def,
                cred_def_id=credential_definition_id,
            )
            for credential_definition_id in credential_definition_ids
        ]

        # Wait for completion of retrieval and transform all credential definitions
        # into response model (if a credential definition was returned)
        if get_credential_definition_futures:
            bound_logger.debug("Getting definitions from fetched credential ids")
            credential_definition_results = await asyncio.gather(
                *get_credential_definition_futures
            )
        else:
            bound_logger.debug("No definition ids returned")
            credential_definition_results = []

    credential_definitions = [
        credential_definition_from_acapy(credential_definition.credential_definition)
        for credential_definition in credential_definition_results
        if credential_definition.credential_definition
    ]

    if credential_definitions:
        bound_logger.info("Successfully fetched credential definitions.")
    else:
        bound_logger.info("No credential definitions matching request.")

    return credential_definitions


@router.get(
    "/credentials/{credential_definition_id}",
    summary="Get a Credential Definition",
    response_model=CredentialDefinition,
)
async def get_credential_definition_by_id(
    credential_definition_id: str,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> CredentialDefinition:
    """
    Get credential definition by id
    ---
    This endpoint returns information for a credential definition.

    Anyone can call this, whether they created the requested credential definition or not.
    Practically it will just reveal the schema that was used for the credential definition.

    Parameters:
    ---
        credential_definition_id: str
            credential definition id

    Returns:
    ---
        CredentialDefinition
            The credential definition
    """
    bound_logger = logger.bind(
        body={"credential_definition_id": credential_definition_id}
    )
    bound_logger.info("GET request received: Get credential definition by id")

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Getting credential definition")
        credential_definition = await handle_acapy_call(
            logger=bound_logger,
            acapy_call=aries_controller.credential_definition.get_cred_def,
            cred_def_id=credential_definition_id,
        )

        if not credential_definition.credential_definition:
            bound_logger.info("Bad request: credential definition id not found.")
            raise HTTPException(
                404,
                f"Credential Definition with id {credential_definition_id} not found.",
            )

        bound_logger.debug("Cast credential definition response to model")
        cloudapi_credential_definition = credential_definition_from_acapy(
            credential_definition.credential_definition
        )

        # We need to update the schema_id on the returned credential definition as
        # ACA-Py returns the schema_id as the seq_no
        bound_logger.debug("Fetching schema associated with definition's schema id")
        schema = await get_schema(
            schema_id=cloudapi_credential_definition.schema_id,
            auth=auth,
        )
        cloudapi_credential_definition.schema_id = schema.id

    bound_logger.info("Successfully fetched credential definition.")
    return cloudapi_credential_definition
