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
    get_schemas,
)
from app.tests.util.regression_testing import (
    TestMode,
    assert_fail_on_recreating_fixtures,
)
from app.tests.util.trust_registry import register_issuer
from app.util.string import random_version
from shared import RichAsyncClient


async def fetch_or_create_regression_test_schema_definition(
    name, auth
) -> CredentialSchema:
    regression_test_schema_name = "Regression_" + name

    schemas = await get_schemas(schema_name=regression_test_schema_name, auth=auth)
    num_schemas = len(schemas)
    assert (
        num_schemas < 2
    ), f"Should have 1 or 0 schemas with this name, got: {num_schemas}"

    if schemas:
        schema_definition_result = schemas[0]
    else:
        # Schema not created yet
        assert_fail_on_recreating_fixtures()
        definition = CreateSchema(
            name=regression_test_schema_name,
            version="1.0.0",
            attribute_names=["speed", "name", "age"],
        )

        schema_definition_result = await create_schema(definition, auth)

    return schema_definition_result


async def get_clean_or_regression_test_schema(name, auth, test_mode):
    if test_mode == TestMode.clean_run:
        definition = CreateSchema(
            name=name,
            version=random_version(),
            attribute_names=["speed", "name", "age"],
        )

        schema_definition_result = await create_schema(definition, auth)
    elif test_mode == TestMode.regression_run:
        schema_definition_result = (
            await fetch_or_create_regression_test_schema_definition(name, auth)
        )
    return schema_definition_result


@pytest.fixture(scope="session", params=TestMode.fixture_params)
async def schema_definition(
    request,
    mock_governance_auth: AcaPyAuthVerified,
) -> CredentialSchema:
    return await get_clean_or_regression_test_schema(
        name="test_schema", auth=mock_governance_auth, test_mode=request.param
    )


@pytest.fixture(scope="session", params=TestMode.fixture_params)
async def schema_definition_alt(
    request,
    mock_governance_auth: AcaPyAuthVerified,
) -> CredentialSchema:
    return await get_clean_or_regression_test_schema(
        name="test_schema_alt", auth=mock_governance_auth, test_mode=request.param
    )


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
