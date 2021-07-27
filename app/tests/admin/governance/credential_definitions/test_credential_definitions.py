import ledger_facade
import pytest
import utils
from admin.governance.credential_definitions import (
    CredentialDefinition,
    create_credential_definition,
    get_created_credential_definitions,
    get_credential_definition,
)
from admin.governance.schemas import SchemaDefinition, create_schema
from assertpy import assert_that
from tests.utils_test import get_random_string

base_path = "/admin/governance/credential-definitions"


@pytest.fixture
def setup_local_env():
    utils.is_multitenant = False
    utils.yoma_agent_url = "http://localhost:3021"
    ledger_facade.LEDGER_TYPE = "von"


@pytest.mark.asyncio
async def test_create_credential_definition(
    setup_local_env, yoma_agent_mock, public_did
):
    # given
    definition = SchemaDefinition(name="x", version="0.1", attributes=["average"])

    print(f" created did:{public_did}")
    schema_definition_result = await create_schema(definition, yoma_agent_mock)
    print(schema_definition_result)

    credential_definition = CredentialDefinition(
        schema_id=schema_definition_result["schema_id"],
        tag=get_random_string(5),
        support_revocation=False,
    )

    # when
    result = await create_credential_definition(credential_definition, yoma_agent_mock)

    # then
    written = await get_credential_definition(
        result["credential_definition_id"], yoma_agent_mock
    )
    assert_that(written).is_not_empty().contains_key("credential_definition")
    assert_that(written["credential_definition"]["tag"]).is_equal_to(
        credential_definition.tag
    )


@pytest.mark.asyncio
async def test_create_credential_definition_via_web(
    setup_local_env, yoma_agent_mock, async_client, public_did
):
    # given
    definition = SchemaDefinition(name="x", version="0.1", attributes=["average"])

    print(f" created did:{public_did}")
    schema_definition_result = await create_schema(definition, yoma_agent_mock)
    print(schema_definition_result)

    credential_definition = CredentialDefinition(
        schema_id=schema_definition_result["schema_id"],
        tag=get_random_string(5),
        support_revocation=False,
    )

    # when
    result = (
        await async_client.post(
            f"{base_path}",
            data=(credential_definition.json()),
            headers={
                "x-api-key": "adminApiKey",
                "x-role": "yoma",
                "content-type": "application/json",
            },
        )
    ).json()

    # then
    written = await get_credential_definition(
        result["credential_definition_id"], yoma_agent_mock
    )
    assert_that(written).is_not_empty().contains_key("credential_definition")
    assert_that(written["credential_definition"]["tag"]).is_equal_to(
        credential_definition.tag
    )


@pytest.mark.asyncio
async def test_get_credential_definitions(setup_local_env, yoma_agent_mock, public_did):
    # given
    definition1 = SchemaDefinition(name="x", version="0.1", attributes=["average"])
    definition2 = SchemaDefinition(name="y", version="0.1", attributes=["average"])

    print(f" created did:{public_did}")
    schema_definition_result_1 = await create_schema(definition1, yoma_agent_mock)
    schema_definition_result_2 = await create_schema(definition2, yoma_agent_mock)

    credential_definition_1 = CredentialDefinition(
        schema_id=schema_definition_result_1["schema_id"],
        tag="tag",
        support_revocation=False,
    )
    credential_definition_2 = CredentialDefinition(
        schema_id=schema_definition_result_2["schema_id"],
        tag="tag",
        support_revocation=False,
    )

    await create_credential_definition(credential_definition_1, yoma_agent_mock)
    credential_definition_result_2 = await create_credential_definition(
        credential_definition_2, yoma_agent_mock
    )

    # when
    credential_definition = await get_created_credential_definitions(
        schema_id=schema_definition_result_2["schema_id"],
        aries_controller=yoma_agent_mock,
    )

    # then
    assert_that(credential_definition["credential_definition_ids"]).contains_only(
        credential_definition_result_2["credential_definition_id"]
    )


@pytest.mark.asyncio
async def test_get_credential_definitions_via_web(
    setup_local_env, yoma_agent_mock, async_client, public_did
):
    # given
    definition = SchemaDefinition(name="x", version="0.1", attributes=["average"])

    print(f" created did:{public_did}")
    schema_definition_result = await create_schema(definition, yoma_agent_mock)

    credential_definition = CredentialDefinition(
        schema_id=schema_definition_result["schema_id"],
        tag="tag",
        support_revocation=False,
    )

    credential_definition_result = await create_credential_definition(
        credential_definition, yoma_agent_mock
    )

    # when
    credential_definition = (
        await async_client.get(
            f"{base_path}/created",
            params={"schema_id": schema_definition_result["schema_id"]},
            headers={"x-api-key": "adminApiKey", "x-role": "yoma"},
        )
    ).json()

    # then
    assert_that(credential_definition["credential_definition_ids"]).contains_only(
        credential_definition_result["credential_definition_id"]
    )


@pytest.mark.asyncio
async def test_get_credential_definition(setup_local_env, yoma_agent_mock, public_did):
    # given
    definition1 = SchemaDefinition(name="x", version="0.1", attributes=["average"])

    schema_definition_result_1 = await create_schema(definition1, yoma_agent_mock)

    credential_definition_1 = CredentialDefinition(
        schema_id=schema_definition_result_1["schema_id"],
        tag=get_random_string(5),
        support_revocation=False,
    )

    credential_definition_result = await create_credential_definition(
        credential_definition_1, yoma_agent_mock
    )

    # when
    result = await get_credential_definition(
        credential_definition_result["credential_definition_id"], yoma_agent_mock
    )

    # then
    assert_that(result).contains_key("credential_definition")
    assert_that(result["credential_definition"]).is_not_none()
    assert_that(result["credential_definition"]["tag"]).is_equal_to(
        credential_definition_1.tag
    )


@pytest.mark.asyncio
async def test_get_credential_definition_via_web(
    setup_local_env, yoma_agent_mock, async_client, public_did
):
    # given
    definition1 = SchemaDefinition(name="x", version="0.1", attributes=["average"])
    schema_definition_result_1 = await create_schema(definition1, yoma_agent_mock)
    credential_definition_1 = CredentialDefinition(
        schema_id=schema_definition_result_1["schema_id"],
        tag=get_random_string(5),
        support_revocation=False,
    )
    credential_definition_result = await create_credential_definition(
        credential_definition_1, yoma_agent_mock
    )
    # when
    result_json = (
        await async_client.get(
            f"{base_path}/{credential_definition_result['credential_definition_id']}",
            headers={"x-api-key": "adminApiKey", "x-role": "yoma"},
        )
    ).json()
    # then
    assert_that(result_json).contains_key("credential_definition")
    assert_that(result_json["credential_definition"]).is_not_none()
    assert_that(result_json["credential_definition"]["tag"]).is_equal_to(
        credential_definition_1.tag
    )
