import asyncio
from dataclasses import dataclass
from logging import Logger
from typing import List, Optional

from aries_cloudcontroller import (
    AcaPyClient,
    CredentialDefinitionSendRequest,
    SchemaGetResult,
    SchemaSendRequest,
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
from app.routes.trust_registry import (
    get_schema_by_id as get_trust_registry_schema_by_id,
)
from app.routes.trust_registry import get_schemas as get_trust_registry_schemas
from app.services import acapy_wallet
from app.services.revocation_registry import wait_for_active_registry
from app.services.trust_registry.schemas import register_schema
from app.services.trust_registry.util.issuer import assert_valid_issuer
from app.util.definitions import (
    credential_definition_from_acapy,
    credential_schema_from_acapy,
)
from app.util.retry_method import coroutine_with_retry_until_value
from shared import ACAPY_ENDORSER_ALIAS, REGISTRY_CREATION_TIMEOUT


@dataclass
class ServiceDependencies:
    logger: Logger
    aries_controller: AcaPyClient


class SchemaPublisher:
    def __init__(self, deps: ServiceDependencies):
        self.deps = deps

    async def publish_schema(self, schema_request: SchemaSendRequest):
        result = await handle_acapy_call(
            logger=self.deps.logger,
            acapy_call=self.deps.aries_controller.schema.publish_schema,
            body=schema_request,
            create_transaction_for_endorser=False,
        )
        return result

    async def handle_existing_schema(self, schema: CreateSchema):
        self.deps.logger.info("Handling case of schema already existing on ledger")
        self.deps.logger.debug("Fetching public DID for governance controller")
        pub_did = await handle_acapy_call(
            logger=self.deps.logger,
            acapy_call=self.deps.aries_controller.wallet.get_public_did,
        )

        _schema_id = f"{pub_did.result.did}:2:{schema.name}:{schema.version}"
        self.deps.logger.debug(
            "Fetching schema id `{}` which is associated with request",
            _schema_id,
        )

        _schema: SchemaGetResult = await handle_acapy_call(
            logger=self.deps.logger,
            acapy_call=self.deps.aries_controller.schema.get_schema,
            schema_id=_schema_id,
        )

        # Edge case where the governance agent has changed its public did
        # Then we need to retrieve the schema in a different way as constructing the schema ID the way above
        # will not be correct due to different public did.
        if _schema.var_schema is None:
            self.deps.logger.debug(
                "Schema not found. Governance agent may have changed public DID. "
                "Fetching schemas created by governance agent with request name and version"
            )
            schemas_created_ids = await handle_acapy_call(
                logger=self.deps.logger,
                acapy_call=self.deps.aries_controller.schema.get_created_schemas,
                schema_name=schema.name,
                schema_version=schema.version,
            )
            self.deps.logger.debug("Getting schemas associated with fetched ids")
            schemas: List[SchemaGetResult] = [
                await handle_acapy_call(
                    logger=self.deps.logger,
                    acapy_call=self.deps.aries_controller.schema.get_schema,
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
                self.deps.logger.debug("Using updated schema id with new DID")
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
            self.deps.logger.info(
                "Schema already exists on ledger. Returning schema definition: `{}`.",
                result,
            )
            return result


class SchemaRegistrar:
    def __init__(self, deps: ServiceDependencies):
        self.deps = deps

    async def register_schema(self, schema_id: str):
        self.deps.logger.debug("Registering schema after successful publish to ledger")
        try:
            await register_schema(schema_id=schema_id)
        except TrustRegistryException as error:
            # If status_code is 405 it means the schema already exists in the trust registry
            # That's okay, because we've achieved our intended result:
            #   make sure the schema is registered in the trust registry
            self.deps.logger.info(
                "Caught TrustRegistryException when registering schema. "
                "Got status code {} with message `{}`",
                error.status_code,
                error.detail,
            )
            if error.status_code == 405:
                self.deps.logger.info(
                    "Status code 405 indicates schema is already registered, so we can continue"
                )
            else:
                raise error


async def create_schema_service(
    logger: Logger,
    aries_controller: AcaPyClient,
    schema_request: SchemaSendRequest,
    schema: CreateSchema,
) -> CredentialSchema:
    """
    Create a schema and register it in the trust registry
    """
    deps = ServiceDependencies(logger, aries_controller)
    publisher = SchemaPublisher(deps)
    registrar = SchemaRegistrar(deps)

    try:
        result = await publisher.publish_schema(schema_request)
    except CloudApiException as e:
        if "already exist" in e.detail and e.status_code == 400:
            result = await publisher.handle_existing_schema(schema)
        else:
            logger.warning(
                f"An unhandled Exception was caught while publishing schema: {e.detail}"
            )
            raise CloudApiException("Error while creating schema.") from e

    if result.sent and result.sent.schema_id:
        await registrar.register_schema(result.sent.schema_id)
    else:
        logger.error("No SchemaSendResult in `publish_schema` response.")
        raise CloudApiException(
            "An unexpected error occurred: could not publish schema."
        )

    result = credential_schema_from_acapy(result.sent.var_schema)
    logger.info("Successfully published and registered schema.")
    return result


async def get_schemas_tenant(
    logger: Logger,
    aries_controller: AcaPyClient,
    schema_id: Optional[str],
    schema_issuer_did: Optional[str],
    schema_name: Optional[str],
    schema_version: Optional[str],
) -> List[CredentialSchema]:
    """
    Allows tenants to get all schemas created
    """
    logger.info("GET request received: Get created schemas")

    if not schema_id:  # client is not filtering by schema_id, fetch all
        trust_registry_schemas = await get_trust_registry_schemas()
    else:  # fetch specific id
        trust_registry_schemas = [await get_trust_registry_schema_by_id(schema_id)]

    schema_ids = [schema.id for schema in trust_registry_schemas]

    schemas = await schema_futures(logger, schema_ids, aries_controller)

    if schema_issuer_did:
        schemas = [
            schema for schema in schemas if schema.id.split(":")[0] == schema_issuer_did
        ]
    if schema_name:
        schemas = [schema for schema in schemas if schema.name == schema_name]
    if schema_version:
        schemas = [schema for schema in schemas if schema.version == schema_version]

    return schemas


async def get_schemas_governance(
    logger: Logger,
    aries_controller: AcaPyClient,
    schema_id: Optional[str],
    schema_issuer_did: Optional[str],
    schema_name: Optional[str],
    schema_version: Optional[str],
) -> List[CredentialSchema]:
    """
    Governance agents gets all schemas created by itself
    """
    logger.info("GET request received: Get schemas created by governance client")
    # Get all created schema ids that match the filter
    logger.debug("Fetching created schemas")
    response = await handle_acapy_call(
        logger=logger,
        acapy_call=aries_controller.schema.get_created_schemas,
        schema_id=schema_id,
        schema_issuer_did=schema_issuer_did,
        schema_name=schema_name,
        schema_version=schema_version,
    )

    # Initiate retrieving all schemas
    schema_ids = response.schema_ids or []

    schemas = await schema_futures(logger, schema_ids, aries_controller)

    return schemas


async def schema_futures(
    logger: Logger, schema_ids: List[str], aries_controller: AcaPyClient
) -> List[CredentialSchema]:
    """
    Get schemas with attributes from schema ids
    """
    # We now have schema_ids; the following logic is the same whether called by governance or tenant.
    # Now fetch relevant schemas from ledger:
    get_schema_futures = [
        handle_acapy_call(
            logger=logger,
            acapy_call=aries_controller.schema.get_schema,
            schema_id=schema_id,
        )
        for schema_id in schema_ids
    ]

    # Wait for completion of retrieval and transform all schemas into response model (if a schema was returned)
    if get_schema_futures:
        logger.debug("Fetching each of the created schemas")
        schema_results: List[SchemaGetResult] = await asyncio.gather(
            *get_schema_futures
        )
    else:
        logger.debug("No created schema ids returned")
        schema_results = []

    schemas = [
        credential_schema_from_acapy(schema.var_schema)
        for schema in schema_results
        if schema.var_schema
    ]

    return schemas


class CredDefPublisher:
    def __init__(self, deps: ServiceDependencies):
        self.deps = deps

    async def assert_public_did(self):
        try:
            self.deps.logger.debug("Asserting client has public DID")
            public_did = await acapy_wallet.assert_public_did(self.deps.aries_controller)
        except CloudApiException as e:
            log_message = f"Asserting public DID failed: {e}"

            if e.status_code == 403:
                self.deps.logger.info(log_message)
                client_error_message = (
                    "Wallet making this request has no public DID. "
                    "Only issuers with a public DID can make this request."
                )

            else:
                self.deps.logger.error(log_message)
                client_error_message = (
                    "Something went wrong while asserting if request is from a valid issuer. "
                    "Please try again."
                )
            raise CloudApiException(client_error_message, e.status_code) from e
        return public_did

    async def check_endorser_connection(self):
        endorser_connection = await handle_acapy_call(
            logger=self.deps.logger,
            acapy_call=self.deps.aries_controller.connection.get_connections,
            alias=ACAPY_ENDORSER_ALIAS,
        )
        has_connections = len(endorser_connection.results) > 0

        if not has_connections:
            self.deps.logger.error(
                "Failed to create credential definition supporting revocation: no endorser connection found. "
                "Issuer attempted to create a credential definition with support for revocation but does not "
                "have an active connection with an endorser, which is required for this operation."
            )

            raise CloudApiException(
                "Credential definition creation failed: An active endorser connection is required "
                "to support revocation. Please establish a connection with an endorser and try again."
            )

    async def publish_credential_definition(self, request_body):
        try:
            result = await handle_acapy_call(
                logger=self.deps.logger,
                acapy_call=self.deps.aries_controller.credential_definition.publish_cred_def,
                body=request_body,
            )

        except CloudApiException as e:
            self.deps.logger.warning(
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

        return result

    async def wait_for_transaction_ack(self, transaction_id):
        self.deps.logger.debug(
            "The publish credential definition response provides a transaction id. "
            "Waiting for transaction to be in state `transaction_acked`"
        )
        try:
            # Wait for transaction to be acknowledged and written to the ledger
            await coroutine_with_retry_until_value(
                coroutine_func=self.deps.aries_controller.endorse_transaction.get_transaction,
                args=(transaction_id,),
                field_name="state",
                expected_value="transaction_acked",
                logger=self.deps.logger,
                max_attempts=10,
                retry_delay=2,
            )
        except asyncio.TimeoutError as e:
            raise CloudApiException(
                "Timeout waiting for endorser to accept the endorsement request.",
                504,
            ) from e
        self.deps.logger.debug("Transaction has been acknowledged by the endorser")

    async def wait_for_revocation_registry(self, credential_definition_id):
        try:
            self.deps.logger.debug("Waiting for revocation registry creation")
            await asyncio.wait_for(
                wait_for_active_registry(
                    self.deps.aries_controller, credential_definition_id
                ),
                timeout=REGISTRY_CREATION_TIMEOUT,
            )
        except asyncio.TimeoutError as e:
            self.deps.logger.error("Timeout waiting for revocation registry creation.")
            raise CloudApiException(
                "Timeout waiting for revocation registry creation.",
                504,
            ) from e


async def create_cred_def(
    logger: Logger,
    aries_controller: AcaPyClient,
    credential_definition: CreateCredentialDefinition,
    support_revocation: bool,
) -> str:
    """
    Create a credential definition
    """
    deps = ServiceDependencies(logger, aries_controller)
    publisher = CredDefPublisher(deps)

    public_did = await publisher.assert_public_did()

    await assert_valid_issuer(public_did, credential_definition.schema_id)

    if support_revocation:
        await publisher.check_endorser_connection()

    request_body = handle_model_with_validation(
        logger=logger,
        model_class=CredentialDefinitionSendRequest,
        schema_id=credential_definition.schema_id,
        support_revocation=support_revocation,
        tag=credential_definition.tag,
        revocation_registry_size=32767,
    )

    result = await publisher.publish_credential_definition(request_body)
    credential_definition_id = result.sent.credential_definition_id

    if result.txn and result.txn.transaction_id:
        await publisher.wait_for_transaction_ack(result.txn.transaction_id)

    if support_revocation:
        await publisher.wait_for_revocation_registry(credential_definition_id)

    return credential_definition_id


async def get_cred_defs(
    logger: Logger,
    aries_controller: AcaPyClient,
    issuer_did: Optional[str],
    credential_definition_id: Optional[str],
    schema_id: Optional[str],
    schema_issuer_did: Optional[str],
    schema_name: Optional[str],
    schema_version: Optional[str],
) -> List[CredentialDefinition]:
    """
    Get credential definitions
    """

    logger.debug("Getting created credential definitions")
    response = await handle_acapy_call(
        logger=logger,
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
            logger=logger,
            acapy_call=aries_controller.credential_definition.get_cred_def,
            cred_def_id=credential_definition_id,
        )
        for credential_definition_id in credential_definition_ids
    ]

    # Wait for completion of retrieval and transform all credential definitions
    # into response model (if a credential definition was returned)
    if get_credential_definition_futures:
        logger.debug("Getting definitions from fetched credential ids")
        credential_definition_results = await asyncio.gather(
            *get_credential_definition_futures
        )
    else:
        logger.debug("No definition ids returned")
        credential_definition_results = []

    credential_definitions = [
        credential_definition_from_acapy(credential_definition.credential_definition)
        for credential_definition in credential_definition_results
        if credential_definition.credential_definition
    ]

    return credential_definitions
