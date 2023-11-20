import asyncio
import json
import time
from typing import List, Optional

from aries_cloudcontroller import (
    AcaPyClient,
    ApiException,
    CredentialDefinitionSendRequest,
    RevRegUpdateTailsFileUri,
    SchemaGetResult,
    SchemaSendRequest,
)
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies.acapy_clients import client_from_auth, get_governance_controller
from app.dependencies.auth import (
    AcaPyAuth,
    AcaPyAuthVerified,
    acapy_auth,
    acapy_auth_governance,
    acapy_auth_verified,
)
from app.event_handling.sse_listener import SseListener
from app.exceptions import CloudApiException, TrustRegistryException
from app.models.definitions import (
    CreateCredentialDefinition,
    CreateSchema,
    CredentialDefinition,
    CredentialSchema,
)
from app.services import acapy_wallet
from app.services.revocation_registry import (
    create_revocation_registry,
    publish_revocation_registry_on_ledger,
)
from app.services.trust_registry.schemas import register_schema
from app.services.trust_registry.util.issuer import assert_valid_issuer
from app.util.definitions import (
    credential_definition_from_acapy,
    credential_schema_from_acapy,
)
from shared import ACAPY_ENDORSER_ALIAS, ACAPY_TAILS_SERVER_BASE_URL
from shared.log_config import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/generic/definitions",
    tags=["definitions"],
)


@router.get("/credentials", response_model=List[CredentialDefinition])
async def get_credential_definitions(
    issuer_did: Optional[str] = None,
    credential_definition_id: Optional[str] = None,
    schema_id: Optional[str] = None,
    schema_issuer_did: Optional[str] = None,
    schema_name: Optional[str] = None,
    schema_version: Optional[str] = None,
    auth: AcaPyAuth = Depends(acapy_auth),
) -> List[CredentialDefinition]:
    """
        Get agent-created credential definitions

    Parameters:
    ---
        issuer_did: Optional[str]
        credential_definition_id: Optional[str]
        schema_id: Optional[str]
        schema_issuer_id: Optional[str]
        schema_version: Optional[str]

    Returns:
    ---
        Created credential definitions
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
    "/credentials/{credential_definition_id}", response_model=CredentialDefinition
)
async def get_credential_definition_by_id(
    credential_definition_id: str,
    auth: AcaPyAuth = Depends(acapy_auth),
) -> CredentialDefinition:
    """
        Get credential definition by id.

    Parameters:
    -----------
        credential_definition_id: str
            credential definition id

    """
    bound_logger = logger.bind(
        body={"credential_definition_id": credential_definition_id}
    )
    bound_logger.info("GET request received: Get credential definition by id")

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Getting credential definition")
        credential_definition = (
            await aries_controller.credential_definition.get_cred_def(
                cred_def_id=credential_definition_id
            )
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


@router.post("/credentials", response_model=CredentialDefinition)
async def create_credential_definition(
    credential_definition: CreateCredentialDefinition,
    auth: AcaPyAuthVerified = Depends(acapy_auth_verified),
) -> CredentialDefinition:
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
    bound_logger = logger.bind(body=credential_definition)
    bound_logger.info("POST request received: Create credential definition")

    async with client_from_auth(auth) as aries_controller:
        # Assert the agent has a public did
        bound_logger.debug("Asserting client has public DID")
        public_did = await acapy_wallet.assert_public_did(aries_controller)

        # Make sure we are allowed to issue this schema according to trust registry rules
        bound_logger.debug("Asserting client is a valid issuer")
        await assert_valid_issuer(public_did, credential_definition.schema_id)

        listener = SseListener(topic="endorsements", wallet_id=auth.wallet_id)

        bound_logger.debug("Publishing credential definition")
        result = await aries_controller.credential_definition.publish_cred_def(
            body=CredentialDefinitionSendRequest(
                schema_id=credential_definition.schema_id,
                support_revocation=credential_definition.support_revocation,
                tag=credential_definition.tag,
            )
        )

        if result.txn and result.txn.transaction_id:
            bound_logger.debug(
                "The publish credential definition response provides a transaction id. "
                "Waiting for transaction to be in state `transaction-acked`"
            )
            try:
                # Wait for transaction to be acknowledged and written to the ledger
                await listener.wait_for_event(
                    field="transaction_id",
                    field_id=result.txn.transaction_id,
                    desired_state="transaction-acked",
                )
            except asyncio.TimeoutError:
                raise CloudApiException(
                    "Timeout waiting for endorser to accept the endorsement request.",
                    504,
                )
            bound_logger.debug(
                "Transaction has been acknowledged. Fetching transaction"
            )

            try:
                transaction = (
                    await aries_controller.endorse_transaction.get_transaction(
                        tran_id=result.txn.transaction_id
                    )
                )
                bound_logger.debug("Transaction fetched successfully")

                # Based on
                # https://github.com/bcgov/traction/blob/6c86d35f3e8b8ca0b88a198876155ba820fb34ea/services/traction/api/services/SchemaWorkflow.py#L276-L280
                signatures = transaction.signature_response[0]["signature"]
                endorser_public_did = list(signatures.keys())[0]
                signature = json.loads(signatures[endorser_public_did])

                public_did = signature["identifier"]
                sig_type = signature["operation"]["signature_type"]
                schema_ref = signature["operation"]["ref"]
                tag = signature["operation"]["tag"]
                credential_definition_id = (
                    f"{public_did}:3:{sig_type}:{schema_ref}:{tag}"
                )
            except Exception as e:
                raise CloudApiException(
                    "Unable to construct credential definition id from signature response."
                ) from e
        elif result.sent and result.sent.credential_definition_id:
            bound_logger.debug(
                "The publish credential definition response does not provide a transaction id, "
                "but it does provide a sent `credential_definition_id`"
            )
            credential_definition_id = result.sent.credential_definition_id
        else:
            raise CloudApiException(
                "Missing both `credential_definition_id` and `transaction_id` from response after publishing cred def."
            )
        # Temporary workaround for "Not issuer of credential definition" error PR #469
        time.sleep(1)
        if credential_definition.support_revocation:
            bound_logger.debug("Supporting revocation. Creating revocation registry")
            try:
                # Create a revocation registry and publish it on the ledger
                revoc_reg_creation_result = await create_revocation_registry(
                    controller=aries_controller,
                    credential_definition_id=credential_definition_id,
                    max_cred_num=credential_definition.revocation_registry_size,
                )
                bound_logger.debug("Updating revocation registry")
                await aries_controller.revocation.update_registry(
                    rev_reg_id=revoc_reg_creation_result.revoc_reg_id,
                    body=RevRegUpdateTailsFileUri(
                        tails_public_uri=f"{ACAPY_TAILS_SERVER_BASE_URL}/{revoc_reg_creation_result.revoc_reg_id}"
                    ),
                )
                bound_logger.debug("Fetching connection with endorser")
                endorser_connection = await aries_controller.connection.get_connections(
                    alias=ACAPY_ENDORSER_ALIAS
                )
                # NOTE: Special case - the endorser registers a cred def itself that
                # supports revocation so there is no endorser connection.
                # Otherwise onboarding should have created an endorser connection
                # for tenants so this fails correctly
                has_connections = len(endorser_connection.results) > 0
                bound_logger.debug("Publish revocation registry")
                await publish_revocation_registry_on_ledger(
                    controller=aries_controller,
                    revocation_registry_id=revoc_reg_creation_result.revoc_reg_id,
                    connection_id=endorser_connection.results[0].connection_id
                    if has_connections
                    else None,
                    create_transaction_for_endorser=has_connections,
                )
                if has_connections:
                    bound_logger.debug(
                        "Issuer has connection with endorser. "
                        "Await transaction to be in state `request-received`"
                    )
                    admin_listener = SseListener(
                        topic="endorsements", wallet_id="admin"
                    )
                    try:
                        txn_record = await admin_listener.wait_for_state(
                            desired_state="request-received"
                        )
                    except TimeoutError:
                        raise CloudApiException(
                            "Timeout occurred while waiting to retrieve transaction record for endorser.",
                            504,
                        )
                    async with get_governance_controller() as endorser_controller:
                        await endorser_controller.endorse_transaction.endorse_transaction(
                            tran_id=txn_record["transaction_id"]
                        )
                else:
                    bound_logger.debug("Issuer has no connection with endorser")

                bound_logger.debug("Setting registry state to `active`")
                active_rev_reg = await aries_controller.revocation.set_registry_state(
                    rev_reg_id=revoc_reg_creation_result.revoc_reg_id, state="active"
                )
                credential_definition_id = active_rev_reg.result.cred_def_id
            except ApiException as e:
                bound_logger.debug(
                    "An ApiException was caught while supporting revocation. The error message is: '{}'.",
                    e.reason,
                )
                raise e

    # ACA-Py only returns the id after creating a credential definition
    # We want consistent return types across all endpoints, so retrieving the credential
    # definition here.
    result = await get_credential_definition_by_id(credential_definition_id, auth)
    bound_logger.info("Successfully created credential definition.")
    return result


@router.get("/schemas", response_model=List[CredentialSchema])
async def get_schemas(
    schema_id: Optional[str] = None,
    schema_issuer_did: Optional[str] = None,
    schema_name: Optional[str] = None,
    schema_version: Optional[str] = None,
    auth: AcaPyAuth = Depends(acapy_auth),
) -> List[CredentialSchema]:
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
        son response with created schemas from ledger.
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


@router.get("/schemas/{schema_id}", response_model=CredentialSchema)
async def get_schema(
    schema_id: str,
    auth: AcaPyAuth = Depends(acapy_auth),
) -> CredentialSchema:
    """
        Retrieve schema by id.

    Parameters:
    -----------
        schema_id: str
            schema id
    """
    bound_logger = logger.bind(body={"schema_id": schema_id})
    bound_logger.info("GET request received: Get schema by id")

    async with client_from_auth(auth) as aries_controller:
        bound_logger.debug("Fetching schema")
        schema = await aries_controller.schema.get_schema(schema_id=schema_id)

    if not schema.var_schema:
        bound_logger.info("Bad request: schema id not found.")
        raise HTTPException(404, f"Schema with id {schema_id} not found.")

    result = credential_schema_from_acapy(schema.var_schema)
    bound_logger.info("Successfully fetched schema by id.")
    return result


@router.post("/schemas", response_model=CredentialSchema)
async def create_schema(
    schema: CreateSchema,
    # Only governance can create schemas
    governance_auth: AcaPyClient = Depends(acapy_auth_governance),
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
    bound_logger = logger.bind(body=schema)
    bound_logger.info("POST request received: Create schema (publish and register)")

    schema_send_request = SchemaSendRequest(
        attributes=schema.attribute_names,
        schema_name=schema.name,
        schema_version=schema.version,
    )
    async with get_governance_controller() as aries_controller:
        try:
            bound_logger.info("Publishing schema as governance")
            result = await aries_controller.schema.publish_schema(
                body=schema_send_request, create_transaction_for_endorser=False
            )
        except ApiException as e:
            bound_logger.info(
                "ApiException caught while trying to publish schema: `{}`",
                e.reason,
            )
            if e.status == 400 and "already exist" in e.reason:
                bound_logger.info("Handling case of schema already existing on ledger")
                bound_logger.debug("Fetching public DID for governance controller")
                pub_did = await aries_controller.wallet.get_public_did()

                _schema_id = f"{pub_did.result.did}:2:{schema.name}:{schema.version}"
                bound_logger.debug(
                    "Fetching schema id `{}` which is associated with request",
                    _schema_id,
                )
                _schema: SchemaGetResult = await aries_controller.schema.get_schema(
                    schema_id=_schema_id
                )
                # Edge case where the governance agent has changed its public did
                # Then we need to retrieve the schema in a different way as constructing the schema ID the way above
                # will not be correct due to different public did.
                if _schema.var_schema is None:
                    bound_logger.debug(
                        "Schema not found. Governance agent may have changed public DID. "
                        "Fetching schemas created by governance agent with request name and version"
                    )
                    schemas_created_ids = (
                        await aries_controller.schema.get_created_schemas(
                            schema_name=schema.name, schema_version=schema.version
                        )
                    )
                    bound_logger.debug("Getting schemas associated with fetched ids")
                    schemas: List[SchemaGetResult] = [
                        await aries_controller.schema.get_schema(schema_id=schema_id)
                        for schema_id in schemas_created_ids.schema_ids
                        if schema_id
                    ]
                    if schemas:
                        if len(schemas) > 1:
                            raise CloudApiException(
                                f"Multiple schemas with name {schema.name} and version {schema.version} exist."
                                + f"These are: `{str(schemas_created_ids.schema_ids)}`.",
                                409,
                            )

                        bound_logger.debug("Using updated schema id with new DID")
                        _schema: SchemaGetResult = schemas[0]
                    else:
                        # if schema already exists, we should at least fetch 1, so this should never happen
                        raise CloudApiException("Could not publish schema.", 500)
                # Schema exists with different attributes
                if set(_schema.var_schema.attr_names) != set(schema.attribute_names):
                    raise CloudApiException(
                        "Error creating schema: Schema already exists with different attribute names."
                        + f"Given: `{str(set(_schema.var_schema.attr_names))}`. "
                        f"Found: `{str(set(schema.attribute_names))}`.",
                        409,
                    )

                result = credential_schema_from_acapy(_schema.var_schema)
                bound_logger.info(
                    "Schema already exists on ledger. Returning schema definition: `{}`.",
                    result,
                )
                return result
            else:
                bound_logger.warning(
                    "An unhandled ApiException was caught while publishing schema. The error message is: '{}'.",
                    e.reason,
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
