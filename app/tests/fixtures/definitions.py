import pytest

from app.dependencies.auth import (
    AcaPyAuthVerified,
    acapy_auth_from_header,
    acapy_auth_verified,
)
from app.models.definitions import CredentialDefinition
from app.routes.definitions import (
    CreateCredentialDefinition,
    CreateSchema,
    CredentialSchema,
    create_credential_definition,
    create_schema,
    get_credential_definitions,
    get_schemas,
)
from app.tests.util.regression_testing import (
    TestMode,
    assert_fail_on_recreating_fixtures,
)
from app.util.string import random_version
from shared import RichAsyncClient


async def fetch_or_create_regression_test_schema_definition(
    name: str, auth: AcaPyAuthVerified
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


async def get_clean_or_regression_test_schema(
    name: str, auth: AcaPyAuthVerified, test_mode: str
):
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


async def fetch_or_create_regression_test_cred_def(
    auth: AcaPyAuthVerified, schema: CredentialSchema, support_revocation: bool
):
    regression_test_cred_def_tag = "RegressionTag"
    schema_id = schema.id

    cred_defs = await get_credential_definitions(schema_id=schema_id, auth=auth)

    filtered_cred_defs = [
        cred_def
        for cred_def in cred_defs
        if cred_def.tag == regression_test_cred_def_tag
    ]

    num_cred_defs = len(filtered_cred_defs)
    assert (
        num_cred_defs < 2
    ), f"Should have 1 or 0 cred defs with this tag, got: {num_cred_defs}"

    if filtered_cred_defs:
        result = filtered_cred_defs[0]
    else:
        # Cred defs not created yet
        assert_fail_on_recreating_fixtures()

        definition = CreateCredentialDefinition(
            tag=regression_test_cred_def_tag,
            schema_id=schema.id,
            support_revocation=support_revocation,
        )
        result = await create_credential_definition(
            credential_definition=definition, auth=auth
        )
    return result


async def get_clean_or_regression_test_cred_def(
    test_mode: str,
    auth: AcaPyAuthVerified,
    schema: CredentialSchema,
    support_revocation: bool,
) -> CredentialDefinition:
    if test_mode == TestMode.clean_run:
        definition = CreateCredentialDefinition(
            tag="tag",
            schema_id=schema.id,
            support_revocation=support_revocation,
        )
        result = await create_credential_definition(
            credential_definition=definition, auth=auth
        )

    elif test_mode == TestMode.regression_run:
        result = await fetch_or_create_regression_test_cred_def(
            auth=auth, schema=schema, support_revocation=support_revocation
        )
    return result


@pytest.fixture(scope="module", params=TestMode.fixture_params)
async def credential_definition_id(
    request,
    schema_definition: CredentialSchema,  # pylint: disable=redefined-outer-name
    faber_client: RichAsyncClient,
) -> str:
    auth = acapy_auth_verified(
        acapy_auth_from_header(faber_client.headers["x-api-key"])
    )
    result = await get_clean_or_regression_test_cred_def(
        test_mode=request.param,
        auth=auth,
        schema=schema_definition,
        support_revocation=False,
    )
    return result.id


@pytest.fixture(scope="module", params=TestMode.fixture_params)
async def credential_definition_id_revocable(
    request,
    schema_definition_alt: CredentialSchema,  # pylint: disable=redefined-outer-name
    faber_client: RichAsyncClient,
) -> str:
    auth = acapy_auth_verified(
        acapy_auth_from_header(faber_client.headers["x-api-key"])
    )
    result = await get_clean_or_regression_test_cred_def(
        test_mode=request.param,
        auth=auth,
        schema=schema_definition_alt,
        support_revocation=True,
    )
    return result.id


@pytest.fixture(scope="module", params=TestMode.fixture_params)
async def meld_co_credential_definition_id(
    request,
    schema_definition: CredentialSchema,  # pylint: disable=redefined-outer-name
    meld_co_client: RichAsyncClient,
) -> str:
    auth = acapy_auth_verified(
        acapy_auth_from_header(meld_co_client.headers["x-api-key"])
    )
    result = await get_clean_or_regression_test_cred_def(
        test_mode=request.param,
        auth=auth,
        schema=schema_definition,
        support_revocation=False,
    )
    return result.id