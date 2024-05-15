import asyncio
from typing import List, Optional

from aries_cloudcontroller import (
    CredentialDefinitionSendRequest,
    SchemaGetResult,
    SchemaSendRequest,
)
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies.acapy_clients import client_from_auth, get_governance_controller
from app.dependencies.auth import (
    AcaPyAuth,
    AcaPyAuthVerified,
    acapy_auth_from_header,
    acapy_auth_governance,
    acapy_auth_verified,
)
from app.exceptions import (
    CloudApiException,
    TrustRegistryException,
    handle_acapy_call,
    handle_model_with_validation,
)
from app.models.definitions import (
    CreateCredentialDefinition,
    CreateSchema,
    CredentialDefinition,
    CredentialSchema,
)
from app.services import acapy_wallet
from app.services.revocation_registry import wait_for_active_registry
from app.services.trust_registry.schemas import register_schema
from app.services.trust_registry.util.issuer import assert_valid_issuer
from app.util.definitions import (
    credential_definition_from_acapy,
    credential_schema_from_acapy,
)
from app.util.retry_method import coroutine_with_retry, coroutine_with_retry_until_value
from shared import ACAPY_ENDORSER_ALIAS, REGISTRY_CREATION_TIMEOUT
from shared.log_config import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/v1/definitions",
    tags=["definitions"],
)


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

    If revocation is requested ("support_revocation": true), revocation registries will be created.

    **NB**: The creation of these revocation registries can take up to one minute.

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
    This endpoint returns all credential definitions created by the tenant.
    Remember only issuers can create credential definitions.

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
    This endpoint returns a credential definition by id.

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


@router.post("/schemas", summary="Create a new Schema", response_model=CredentialSchema)
async def create_schema(
    schema: CreateSchema,
    # Only governance can create schemas
    governance_auth: AcaPyAuthVerified = Depends(acapy_auth_governance),
) -> CredentialSchema:
    """
    Create a new schema
    ---
    This endpoint creates a new schema.
    Only tenants with the governance role can create schemas.

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
        try:
            bound_logger.info("Publishing schema as governance")
            result = await handle_acapy_call(
                logger=bound_logger,
                acapy_call=aries_controller.schema.publish_schema,
                body=schema_send_request,
                create_transaction_for_endorser=False,
            )
        except CloudApiException as e:
            bound_logger.info(
                "An Exception was caught while trying to publish schema: `{}`",
                e.detail,
            )
            if e.status_code == 400 and "already exist" in e.detail:
                bound_logger.info("Handling case of schema already existing on ledger")
                bound_logger.debug("Fetching public DID for governance controller")
                pub_did = await handle_acapy_call(
                    logger=bound_logger,
                    acapy_call=aries_controller.wallet.get_public_did,
                )

                _schema_id = f"{pub_did.result.did}:2:{schema.name}:{schema.version}"
                bound_logger.debug(
                    "Fetching schema id `{}` which is associated with request",
                    _schema_id,
                )
                _schema: SchemaGetResult = await handle_acapy_call(
                    logger=bound_logger,
                    acapy_call=aries_controller.schema.get_schema,
                    schema_id=_schema_id,
                )
                # Edge case where the governance agent has changed its public did
                # Then we need to retrieve the schema in a different way as constructing the schema ID the way above
                # will not be correct due to different public did.
                if _schema.var_schema is None:
                    bound_logger.debug(
                        "Schema not found. Governance agent may have changed public DID. "
                        "Fetching schemas created by governance agent with request name and version"
                    )
                    schemas_created_ids = await handle_acapy_call(
                        logger=bound_logger,
                        acapy_call=aries_controller.schema.get_created_schemas,
                        schema_name=schema.name,
                        schema_version=schema.version,
                    )
                    bound_logger.debug("Getting schemas associated with fetched ids")
                    schemas: List[SchemaGetResult] = [
                        await handle_acapy_call(
                            logger=bound_logger,
                            acapy_call=aries_controller.schema.get_schema,
                            schema_id=schema_id,
                        )
                        for schema_id in schemas_created_ids.schema_ids
                        if schema_id
                    ]
                    if schemas:
                        if len(schemas) > 1:
                            raise CloudApiException(  # pylint: disable=W0707
                                f"Multiple schemas with name {schema.name} and version {schema.version} exist."
                                + f"These are: `{str(schemas_created_ids.schema_ids)}`.",
                                409,
                            )

                        bound_logger.debug("Using updated schema id with new DID")
                        _schema: SchemaGetResult = schemas[0]
                    else:
                        # if schema already exists, we should at least fetch 1, so this should never happen
                        raise CloudApiException(
                            "Could not publish schema.", 500
                        )  # pylint: disable=W0707
                # Schema exists with different attributes
                if set(_schema.var_schema.attr_names) != set(schema.attribute_names):
                    raise CloudApiException(
                        "Error creating schema: Schema already exists with different attribute names."
                        + f"Given: `{str(set(_schema.var_schema.attr_names))}`. "
                        f"Found: `{str(set(schema.attribute_names))}`.",
                        409,
                    )  # pylint: disable=W0707

                result = credential_schema_from_acapy(_schema.var_schema)
                bound_logger.info(
                    "Schema already exists on ledger. Returning schema definition: `{}`.",
                    result,
                )
                return result
            else:
                bound_logger.warning(
                    "An unhandled Exception was caught while publishing schema. The error message is: '{}'.",
                    e.detail,
                )
                raise CloudApiException("Error while creating schema.") from e

    # Register the schema in the trust registry
    try:
        if result.sent and result.sent.schema_id:
            bound_logger.debug("Registering schema after successful publish to ledger")
            await register_schema(schema_id=result.sent.schema_id)
        else:
            bound_logger.error("No SchemaSendResult in `publish_schema` response.")
            raise CloudApiException(
                "An unexpected error occurred: could not publish schema."
            )
    except TrustRegistryException as error:
        # If status_code is 405 it means the schema already exists in the trust registry
        # That's okay, because we've achieved our intended result:
        #   make sure the schema is registered in the trust registry
        bound_logger.info(
            "Caught TrustRegistryException when registering schema. "
            "Got status code {} with message `{}`",
            error.status_code,
            error.detail,
        )
        if error.status_code == 405:
            bound_logger.info(
                "Status code 405 indicates schema is already registered, so we can continue"
            )
        else:
            raise error

    result = credential_schema_from_acapy(result.sent.var_schema)
    bound_logger.info("Successfully published and registered schema.")
    return result


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
    Get schemas created by the tenant
    ---
    Remember only tenants with the governance role can create schemas,
    i.e. only tenants with the governance role will get a non-empty response.

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
    bound_logger = logger.bind(
        body={
            "schema_id": schema_id,
            "schema_issuer_did": schema_issuer_did,
            "schema_name": schema_name,
            "schema_version": schema_version,
        }
    )
    bound_logger.info("GET request received: Get schemas created by client")

    # Get all created schema ids that match the filter
    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Fetching created schemas")
        response = await handle_acapy_call(
            logger=bound_logger,
            acapy_call=aries_controller.schema.get_created_schemas,
            schema_id=schema_id,
            schema_issuer_did=schema_issuer_did,
            schema_name=schema_name,
            schema_version=schema_version,
        )

        # Initiate retrieving all schemas
        schema_ids = response.schema_ids or []
        get_schema_futures = [
            handle_acapy_call(
                logger=bound_logger,
                acapy_call=aries_controller.schema.get_schema,
                schema_id=schema_id,
            )
            for schema_id in schema_ids
        ]

        # Wait for completion of retrieval and transform all schemas into response model (if a schema was returned)
        if get_schema_futures:
            bound_logger.debug("Fetching each of the created schemas")
            schema_results: List[SchemaGetResult] = await asyncio.gather(
                *get_schema_futures
            )
        else:
            bound_logger.debug("No created schema ids returned")
            schema_results = []

    schemas = [
        credential_schema_from_acapy(schema.var_schema)
        for schema in schema_results
        if schema.var_schema
    ]

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
    This endpoint returns a schema by id.

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
