import json
from contextlib import asynccontextmanager

import acapy_ledger_facade
import acapy_wallet_facade
import ledger_facade
import pytest
import utils
from admin.governance.schemas import SchemaDefinition, create_schema, get_schemas
from assertpy import assert_that

# want to wrap an existing method with a decorator
# the method is normally used by fast api and then fast api manages the tear down
from tests.utils_test import get_random_string

APPLICATION_JSON_CONTENT_TYPE = {"content-type": "application/json"}
BASE_PATH = "/admin/governance/schemas"


@pytest.fixture
def setup_local_env():
    utils.is_multitenant = False
    ledger_facade.LEDGER_TYPE = "von"


@pytest.mark.asyncio
async def test_create_schema_via_web(
    setup_local_env, async_client, yoma_agent_mock, public_did
):
    definition = SchemaDefinition(name="x", version="0.1", attributes=["average"])

    response = await async_client.post(
        BASE_PATH,
        data=json.dumps(definition.dict()),
        headers={
            "x-api-key": "adminApiKey",
            "x-role": "yoma",
            **APPLICATION_JSON_CONTENT_TYPE,
        },
    )
    assert response.status_code == 200
    result = response.json()

    response = await get_schemas(
        schema_id=result["schema_id"], aries_controller=yoma_agent_mock
    )
    assert_that(response["schema_ids"]).is_length(1)


@pytest.mark.asyncio
async def test_get_schemas_via_web(
    setup_local_env, async_client, yoma_agent_mock, public_did
):
    # given
    definition = SchemaDefinition(name="x", version="0.1", attributes=["average"])

    # when
    response = await async_client.post(
        BASE_PATH,
        data=json.dumps(definition.dict()),
        headers={
            "x-api-key": "adminApiKey",
            "x-role": "yoma",
            **APPLICATION_JSON_CONTENT_TYPE,
        },
    )
    assert response.status_code == 200
    result = response.json()

    # then
    response = await async_client.get(
        BASE_PATH,
        params={"schema_id": result["schema_id"]},
        headers={
            "x-api-key": "adminApiKey",
            "x-role": "yoma",
            **APPLICATION_JSON_CONTENT_TYPE,
        },
    )
    assert_that(response.json()["schema_ids"]).is_length(1)


@pytest.mark.asyncio
async def test_get_schema_via_web(
    setup_local_env, async_client, yoma_agent_mock, public_did
):
    # given
    definition = SchemaDefinition(name="x", version="0.1", attributes=["average"])

    response = await async_client.post(
        "/admin/governance/schemas",
        data=json.dumps(definition.dict()),
        headers={
            "x-api-key": "adminApiKey",
            "x-role": "yoma",
            **APPLICATION_JSON_CONTENT_TYPE,
        },
    )
    assert response.status_code == 200
    result = response.json()

    # when
    response = await async_client.get(
        f"{BASE_PATH}/{result['schema_id']}",
        headers={
            "x-api-key": "adminApiKey",
            "x-role": "yoma",
            **APPLICATION_JSON_CONTENT_TYPE,
        },
    )
    # then
    assert_that(response.json()["schema"]["attrNames"]).contains_only("average")


@pytest.mark.asyncio
async def test_create_one_schema(setup_local_env, yoma_agent_mock, public_did):
    # given
    definition = SchemaDefinition(name="x", version="0.1", attributes=["average"])

    print(f" created did:{public_did}")

    # when
    schema_definition_result = await create_schema(definition, yoma_agent_mock)
    print(schema_definition_result)

    # then
    response = await yoma_agent_mock.schema.get_created_schema(
        schema_issuer_did=public_did.did
    )

    assert_that(response["schema_ids"]).contains(schema_definition_result["schema_id"])


@pytest.mark.asyncio
async def test_update_schema(setup_local_env, yoma_agent_mock, public_did):
    # given
    definition1 = SchemaDefinition(name="xya", version="0.1", attributes=["average"])
    definition2 = SchemaDefinition(
        name="xya", version="0.2", attributes=["average", "bitrate"]
    )
    print(f" created did:{public_did}")

    # when
    schema_definition_result_1 = await create_schema(definition1, yoma_agent_mock)
    schema_definition_result_2 = await create_schema(definition2, yoma_agent_mock)

    # then
    response = await yoma_agent_mock.schema.get_created_schema(
        schema_issuer_did=public_did.did
    )

    assert_that(response["schema_ids"]).contains_only(
        schema_definition_result_1["schema_id"],
        schema_definition_result_2["schema_id"],
    )


@pytest.mark.asyncio
async def test_create_two_schemas(setup_local_env, yoma_agent_mock, public_did):
    # given
    definition1 = SchemaDefinition(name="x", version="0.1", attributes=["average"])
    definition2 = SchemaDefinition(name="y", version="0.1", attributes=["average"])

    print(f" created did:{public_did}")

    # when
    schema_definition_result_1 = await create_schema(definition1, yoma_agent_mock)
    schema_definition_result_2 = await create_schema(definition2, yoma_agent_mock)

    # then
    response = await yoma_agent_mock.schema.get_created_schema(
        schema_issuer_did=public_did.did
    )

    assert_that(response["schema_ids"]).contains_only(
        schema_definition_result_1["schema_id"],
        schema_definition_result_2["schema_id"],
    )


@pytest.mark.asyncio
async def test_get_schemas(setup_local_env, yoma_agent_mock, public_did):
    # when
    name = get_random_string(10)
    definition1 = SchemaDefinition(name=name, version="0.1", attributes=["average"])
    definition2 = SchemaDefinition(
        name=name, version="0.2", attributes=["average", "bitrate"]
    )
    print(f" created did:{public_did}")
    schema_definition_result_1 = await create_schema(definition1, yoma_agent_mock)
    schema_definition_result_2 = await create_schema(definition2, yoma_agent_mock)

    # when
    response = await get_schemas(
        schema_issuer_did=public_did.did, aries_controller=yoma_agent_mock
    )

    # then
    assert_that(response["schema_ids"]).contains_only(
        schema_definition_result_1["schema_id"],
        schema_definition_result_2["schema_id"],
    )
    # when
    response = await get_schemas(schema_name=name, aries_controller=yoma_agent_mock)
    # then
    assert_that(response["schema_ids"]).contains_only(
        schema_definition_result_1["schema_id"],
        schema_definition_result_2["schema_id"],
    )

    # when
    response = await get_schemas(
        schema_name=name, schema_version="0.2", aries_controller=yoma_agent_mock
    )
    # then
    assert_that(response["schema_ids"]).contains_only(
        schema_definition_result_2["schema_id"],
    )
