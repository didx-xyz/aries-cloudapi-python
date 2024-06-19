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
