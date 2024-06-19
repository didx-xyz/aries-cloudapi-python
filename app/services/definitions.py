import asyncio
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


async def create_schema_service(
    logger: Logger,
    aries_controller: AcaPyClient,
    schema_request: SchemaSendRequest,
    schema: CreateSchema,
) -> CredentialSchema:
    """
    Create a schema and register it in the trust registry
    """
    try:
        logger.info("Publishing schema as governance")
        result = await handle_acapy_call(
            logger=logger,
            acapy_call=aries_controller.schema.publish_schema,
            body=schema_request,
            create_transaction_for_endorser=False,
        )

    except CloudApiException as e:
        logger.info(
            "An Exception was caught while trying to publish schema: `{}`",
            e.detail,
        )

        if e.status_code == 400 and "already exist" in e.detail:
            logger.info("Handling case of schema already existing on ledger")
            logger.debug("Fetching public DID for governance controller")
            pub_did = await handle_acapy_call(
                logger=logger,
                acapy_call=aries_controller.wallet.get_public_did,
            )

            _schema_id = f"{pub_did.result.did}:2:{schema.name}:{schema.version}"
            logger.debug(
                "Fetching schema id `{}` which is associated with request",
                _schema_id,
            )
            _schema: SchemaGetResult = await handle_acapy_call(
                logger=logger,
                acapy_call=aries_controller.schema.get_schema,
                schema_id=_schema_id,
            )

            # Edge case where the governance agent has changed its public did
            # Then we need to retrieve the schema in a different way as constructing the schema ID the way above
            # will not be correct due to different public did.
            if _schema.var_schema is None:
                logger.debug(
                    "Schema not found. Governance agent may have changed public DID. "
                    "Fetching schemas created by governance agent with request name and version"
                )
                schemas_created_ids = await handle_acapy_call(
                    logger=logger,
                    acapy_call=aries_controller.schema.get_created_schemas,
                    schema_name=schema.name,
                    schema_version=schema.version,
                )
                logger.debug("Getting schemas associated with fetched ids")
                schemas: List[SchemaGetResult] = [
                    await handle_acapy_call(
                        logger=logger,
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

                    logger.debug("Using updated schema id with new DID")
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
            logger.info(
                "Schema already exists on ledger. Returning schema definition: `{}`.",
                result,
            )
            return result

        else:
            logger.warning(
                "An unhandled Exception was caught while publishing schema. The error message is: '{}'.",
                e.detail,
            )
            raise CloudApiException("Error while creating schema.") from e

    # Register the schema in the trust registry
    try:
        if result.sent and result.sent.schema_id:
            logger.debug("Registering schema after successful publish to ledger")
            await register_schema(schema_id=result.sent.schema_id)
        else:
            logger.error("No SchemaSendResult in `publish_schema` response.")
            raise CloudApiException(
                "An unexpected error occurred: could not publish schema."
            )
    except TrustRegistryException as error:
        # If status_code is 405 it means the schema already exists in the trust registry
        # That's okay, because we've achieved our intended result:
        #   make sure the schema is registered in the trust registry
        logger.info(
            "Caught TrustRegistryException when registering schema. "
            "Got status code {} with message `{}`",
            error.status_code,
            error.detail,
        )
        if error.status_code == 405:
            logger.info(
                "Status code 405 indicates schema is already registered, so we can continue"
            )
        else:
            raise error

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
