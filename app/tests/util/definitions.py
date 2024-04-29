import pytest

from app.dependencies.auth import (
    AcaPyAuthVerified,
    acapy_auth_from_header,
    acapy_auth_verified,
)
from app.routes.definitions import (
    CreateCredentialDefinition,
    CreateSchema,
    CredentialSchema,
    create_credential_definition,
    create_schema,
)
from app.tests.util.trust_registry import register_issuer
from app.util.string import random_version
from shared import RichAsyncClient


@pytest.fixture(scope="session")
async def schema_definition(
    mock_governance_auth: AcaPyAuthVerified,
) -> CredentialSchema:
    definition = CreateSchema(
        name="test_schema",
        version=random_version(),
        attribute_names=["speed", "name", "age"],
    )

    schema_definition_result = await create_schema(definition, mock_governance_auth)

    return schema_definition_result


@pytest.fixture(scope="session")
async def schema_definition_alt(
    mock_governance_auth: AcaPyAuthVerified,
) -> CredentialSchema:
    definition = CreateSchema(
        name="test_schema_alt", version=random_version(), attribute_names=["speed"]
    )

    schema_definition_result = await create_schema(definition, mock_governance_auth)

    return schema_definition_result


@pytest.fixture(scope="module")
async def credential_definition_id(
    schema_definition: CredentialSchema,  # pylint: disable=redefined-outer-name
    faber_client: RichAsyncClient,
) -> str:
    await register_issuer(faber_client, schema_definition.id)

    # Support revocation false here because revocation is tested elsewhere.
    # No revocation is a fair bit faster to run
    definition = CreateCredentialDefinition(
        tag="tag", schema_id=schema_definition.id, support_revocation=False
    )

    auth = acapy_auth_verified(
        acapy_auth_from_header(faber_client.headers["x-api-key"])
    )
    result = await create_credential_definition(
        credential_definition=definition, auth=auth
    )

    return result.id


@pytest.fixture(scope="module")
async def credential_definition_id_revocable(
    schema_definition_alt: CredentialSchema,  # pylint: disable=redefined-outer-name
    faber_client: RichAsyncClient,
) -> str:
    await register_issuer(faber_client, schema_definition_alt.id)

    definition = CreateCredentialDefinition(
        tag="tag",
        schema_id=schema_definition_alt.id,
        support_revocation=True,
        revocation_registry_size=2000,
    )

    auth = acapy_auth_verified(
        acapy_auth_from_header(faber_client.headers["x-api-key"])
    )
    result = await create_credential_definition(
        credential_definition=definition, auth=auth
    )

    return result.id


@pytest.fixture(scope="module")
async def meld_co_credential_definition_id(
    schema_definition: CredentialSchema,  # pylint: disable=redefined-outer-name
    meld_co_client: RichAsyncClient,
) -> str:
    await register_issuer(meld_co_client, schema_definition.id)

    # Support revocation false here because revocation is tested elsewhere.
    # No revocation is a fair bit faster to run
    definition = CreateCredentialDefinition(
        tag="tag", schema_id=schema_definition.id, support_revocation=False
    )

    auth = acapy_auth_verified(
        acapy_auth_from_header(meld_co_client.headers["x-api-key"])
    )
    result = await create_credential_definition(
        credential_definition=definition, auth=auth
    )

    return result.id
