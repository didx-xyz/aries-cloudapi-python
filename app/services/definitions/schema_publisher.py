from logging import Logger
from typing import List

from aries_cloudcontroller import AcaPyClient, SchemaGetResult, SchemaSendRequest
from aries_cloudcontroller.models.txn_or_schema_send_result import TxnOrSchemaSendResult

from app.exceptions import CloudApiException, handle_acapy_call
from app.models.definitions import CreateSchema, CredentialSchema
from app.util.definitions import credential_schema_from_acapy


class SchemaPublisher:
    def __init__(
        self,
        controller: AcaPyClient,
        logger: Logger,
    ):
        self._logger = logger
        self._controller = controller

    async def publish_schema(self, schema_request: SchemaSendRequest) -> TxnOrSchemaSendResult:
        result = await handle_acapy_call(
            logger=self._logger,
            acapy_call=self._controller.schema.publish_schema,
            body=schema_request,
            create_transaction_for_endorser=False,
        )
        return result

    async def handle_existing_schema(self, schema: CreateSchema) -> CredentialSchema:
        self._logger.info("Handling case of schema already existing on ledger")
        self._logger.debug("Fetching public DID for governance controller")
        pub_did = await handle_acapy_call(
            logger=self._logger,
            acapy_call=self._controller.wallet.get_public_did,
        )

        _schema_id = f"{pub_did.result.did}:2:{schema.name}:{schema.version}"
        self._logger.debug(
            "Fetching schema id `{}` which is associated with request",
            _schema_id,
        )

        _schema: SchemaGetResult = await handle_acapy_call(
            logger=self._logger,
            acapy_call=self._controller.schema.get_schema,
            schema_id=_schema_id,
        )

        # Edge case where the governance agent has changed its public did
        # Then we need to retrieve the schema in a different way as constructing the schema ID the way above
        # will not be correct due to different public did.
        if _schema.var_schema is None:
            self._logger.debug(
                "Schema not found. Governance agent may have changed public DID. "
                "Fetching schemas created by governance agent with request name and version"
            )
            schemas_created_ids = await handle_acapy_call(
                logger=self._logger,
                acapy_call=self._controller.schema.get_created_schemas,
                schema_name=schema.name,
                schema_version=schema.version,
            )
            self._logger.debug("Getting schemas associated with fetched ids")
            schemas: List[SchemaGetResult] = [
                await handle_acapy_call(
                    logger=self._logger,
                    acapy_call=self._controller.schema.get_schema,
                    schema_id=schema_id,
                )
                for schema_id in schemas_created_ids.schema_ids
                if schema_id
            ]

            if not schemas:
                # if schema already exists, we should at least fetch 1, so this should never happen
                raise CloudApiException(
                    "Could not publish schema.", 500
                )
            if len(schemas) > 1:
                raise CloudApiException(
                    f"Multiple schemas with name {schema.name} and version {schema.version} exist."
                    f"These are: `{str(schemas_created_ids.schema_ids)}`.",
                    409,
                )
            self._logger.debug("Using updated schema id with new DID")
            _schema: SchemaGetResult = schemas[0]

        # Schema exists with different attributes
        if set(_schema.var_schema.attr_names) != set(schema.attribute_names):
            error_message = (
                "Error creating schema: Schema already exists with different attribute names. "
                f"Given: `{str(set(schema.attribute_names))}`. "
                f"Found: `{str(set(_schema.var_schema.attr_names))}`."
            )
            raise CloudApiException(
                error_message,
                409,
            )

        result = credential_schema_from_acapy(_schema.var_schema)
        self._logger.info(
            "Schema already exists on ledger. Returning schema definition: `{}`.",
            result,
        )
        return result

    async def register_schema(self, schema_id: str) -> None:
        self._logger.debug("Registering schema after successful publish to ledger")
        try:
            await register_schema(schema_id=schema_id)
        except TrustRegistryException as error:
            # If status_code is 405 it means the schema already exists in the trust registry
            # That's okay, because we've achieved our intended result:
            #   make sure the schema is registered in the trust registry
            self._logger.info(
                "Caught TrustRegistryException when registering schema. "
                "Got status code {} with message `{}`",
                error.status_code,
                error.detail,
            )
            if error.status_code == 405:
                self._logger.info(
                    "Status code 405 indicates schema is already registered, so we can continue"
                )
            else:
                raise error
