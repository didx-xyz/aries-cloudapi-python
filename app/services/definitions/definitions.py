import asyncio
from typing import List, Optional

from aries_cloudcontroller import (
    AcaPyClient,
    CredentialDefinitionSendRequest,
    SchemaGetResult,
    SchemaSendRequest,
)

from app.exceptions import (
    CloudApiException,
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
from app.services.definitions.credential_definition_publisher import (
    CredentialDefinitionPublisher,
)
from app.services.definitions.schema_publisher import SchemaPublisher
from app.services.trust_registry.schemas import register_schema
from app.services.trust_registry.util.issuer import assert_valid_issuer
from app.util.assert_public_did import assert_public_did
from app.util.definitions import (
    credential_definition_from_acapy,
    credential_schema_from_acapy,
)
from app.util.transaction_acked import wait_for_transaction_ack
from shared.constants import GOVERNANCE_AGENT_URL
from shared.log_config import get_logger

logger = get_logger(__name__)


async def create_schema_service(
    aries_controller: AcaPyClient,
    schema_request: SchemaSendRequest,
    schema: CreateSchema,
) -> CredentialSchema:
    """
    Create a schema and register it in the trust registry
    """
    bound_logger = logger.bind(body=schema)

    publisher = SchemaPublisher(controller=aries_controller, logger=logger)

    try:
        result = await publisher.publish_schema(schema_request)
    except CloudApiException as e:
        if "already exist" in e.detail and e.status_code == 400:
            result = await publisher.handle_existing_schema(schema)
        else:
            bound_logger.warning(
                f"An unhandled Exception was caught while publishing schema: {e.detail}"
            )
            raise CloudApiException("Error while creating schema.") from e

    if result.sent and result.sent.schema_id:
        await register_schema(schema_id=result.sent.schema_id)
    else:
        bound_logger.error("No SchemaSendResult in `publish_schema` response.")
        raise CloudApiException(
            "An unexpected error occurred: could not publish schema."
        )

    result = credential_schema_from_acapy(result.sent.var_schema)
    bound_logger.info("Successfully published and registered schema.")
    return result


async def get_schemas_as_tenant(
    aries_controller: AcaPyClient,
    schema_id: Optional[str] = None,
    schema_issuer_did: Optional[str] = None,
    schema_name: Optional[str] = None,
    schema_version: Optional[str] = None,
) -> List[CredentialSchema]:
    """
    Allows tenants to get all schemas from trust registry
    """
    bound_logger = logger.bind(
        body={
            "schema_id": schema_id,
            "schema_issuer_did": schema_issuer_did,
            "schema_name": schema_name,
            "schema_version": schema_version,
        }
    )
    bound_logger.debug("Fetching schemas from trust registry")

    if not schema_id:  # client is not filtering by schema_id, fetch all
        trust_registry_schemas = await get_trust_registry_schemas()
    else:  # fetch specific id
        trust_registry_schemas = [await get_trust_registry_schema_by_id(schema_id)]

    schema_ids = [schema.id for schema in trust_registry_schemas]

    bound_logger.debug("Getting schemas associated with fetched ids")
    schemas = await get_schemas_by_id(
        aries_controller=aries_controller,
        schema_ids=schema_ids,
    )

    if schema_issuer_did:
        schemas = [
            schema for schema in schemas if schema.id.split(":")[0] == schema_issuer_did
        ]
    if schema_name:
        schemas = [schema for schema in schemas if schema.name == schema_name]
    if schema_version:
        schemas = [schema for schema in schemas if schema.version == schema_version]

    return schemas


async def get_schemas_as_governance(
    aries_controller: AcaPyClient,
    schema_id: Optional[str] = None,
    schema_issuer_did: Optional[str] = None,
    schema_name: Optional[str] = None,
    schema_version: Optional[str] = None,
) -> List[CredentialSchema]:
    """
    Governance agents gets all schemas created by itself
    """
    bound_logger = logger.bind(
        body={
            "schema_id": schema_id,
            "schema_issuer_did": schema_issuer_did,
            "schema_name": schema_name,
            "schema_version": schema_version,
        }
    )

    logger.debug("Asserting governance agent is host being called")
    if aries_controller.configuration.host != GOVERNANCE_AGENT_URL:
        raise CloudApiException(
            "Only governance agents are allowed to access this endpoint.",
            status_code=403,
        )

    # Get all created schema ids that match the filter
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

    bound_logger.debug("Getting schemas associated with fetched ids")
    schemas = await get_schemas_by_id(
        aries_controller=aries_controller,
        schema_ids=schema_ids,
    )

    return schemas


async def get_schemas_by_id(
    aries_controller: AcaPyClient,
    schema_ids: List[str],
) -> List[CredentialSchema]:
    """
    Fetch schemas with attributes using schema IDs.
    The following logic applies to both governance and tenant calls.
    Retrieve the relevant schemas from the ledger:
    """
    logger.debug("Fetching schemas from schema ids")

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


async def create_cred_def(
    aries_controller: AcaPyClient,
    credential_definition: CreateCredentialDefinition,
    support_revocation: bool,
) -> str:
    """
    Create a credential definition
    """
    bound_logger = logger.bind(
        body={
            "schema_id": credential_definition.schema_id,
            "tag": credential_definition.tag,
            "support_revocation": credential_definition.support_revocation,
        }
    )
    publisher = CredentialDefinitionPublisher(
        controller=aries_controller, logger=bound_logger
    )

    public_did = await assert_public_did(aries_controller)

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
        await wait_for_transaction_ack(
            aries_controller=aries_controller, transaction_id=result.txn.transaction_id
        )

    if support_revocation:
        await publisher.wait_for_revocation_registry(credential_definition_id)

    return credential_definition_id


async def get_cred_defs(
    aries_controller: AcaPyClient,
    issuer_did: Optional[str] = None,
    credential_definition_id: Optional[str] = None,
    schema_id: Optional[str] = None,
    schema_issuer_did: Optional[str] = None,
    schema_name: Optional[str] = None,
    schema_version: Optional[str] = None,
) -> List[CredentialDefinition]:
    """
    Get credential definitions
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

    return credential_definitions
