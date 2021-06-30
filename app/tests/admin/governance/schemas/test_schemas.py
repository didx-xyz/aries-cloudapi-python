from contextlib import asynccontextmanager

import json

import pytest
from assertpy import assert_that

import acapy_ledger_facade
import acapy_wallet_facade
import ledger_facade
import utils
from admin.governance.schemas import SchemaDefinition, create_schema, get_schemas

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
async def test_create_schema_via_web(setup_local_env, async_client, yoma_agent):
    definition = SchemaDefinition(name="x", version="0.1", attributes=["average"])

    await create_public_did(yoma_agent)

    response = await async_client.post(
        BASE_PATH,
        data=json.dumps(definition.dict()),
        headers={"x-api-key": "adminApiKey", **APPLICATION_JSON_CONTENT_TYPE},
    )
    assert response.status_code == 200
    result = response.json()

    response = await get_schemas(
        schema_id=result["schema_id"], aries_controller=yoma_agent
    )
    assert_that(response["schema_ids"]).is_length(1)


@pytest.mark.asyncio
async def test_get_schemas_via_web(setup_local_env, async_client, yoma_agent):
    # given
    definition = SchemaDefinition(name="x", version="0.1", attributes=["average"])

    await create_public_did(yoma_agent)

    # when
    response = await async_client.post(
        BASE_PATH,
        data=json.dumps(definition.dict()),
        headers={"x-api-key": "adminApiKey", **APPLICATION_JSON_CONTENT_TYPE},
    )
    assert response.status_code == 200
    result = response.json()

    # then
    response = await async_client.get(
        BASE_PATH,
        params={"schema_id": result["schema_id"]},
        headers={"x-api-key": "adminApiKey", **APPLICATION_JSON_CONTENT_TYPE},
    )
    assert_that(response.json()["schema_ids"]).is_length(1)


@pytest.mark.asyncio
async def test_get_schema_via_web(setup_local_env, async_client, yoma_agent):
    # given
    definition = SchemaDefinition(name="x", version="0.1", attributes=["average"])

    await create_public_did(yoma_agent)
    response = await async_client.post(
        "/admin/governance/schemas",
        data=json.dumps(definition.dict()),
        headers={"x-api-key": "adminApiKey", **APPLICATION_JSON_CONTENT_TYPE},
    )
    assert response.status_code == 200
    result = response.json()

    # when
    response = await async_client.get(
        f"{BASE_PATH}/{result['schema_id']}",
        headers={"x-api-key": "adminApiKey", **APPLICATION_JSON_CONTENT_TYPE},
    )
    # then
    assert_that(response.json()["schema"]["attrNames"]).contains_only("average")


async def create_public_did(aries_agent_controller):
    generate_did_res = await acapy_wallet_facade.create_did(aries_agent_controller)
    did_object = generate_did_res["result"]
    await ledger_facade.post_to_ledger(did_object=did_object)
    # my local von network I was using did not requried the TAA
    taa_response = await acapy_ledger_facade.get_taa(aries_agent_controller)
    await acapy_ledger_facade.accept_taa(aries_agent_controller, taa_response)
    await acapy_wallet_facade.assign_pub_did(aries_agent_controller, did_object["did"])
    return did_object


@pytest.mark.asyncio
async def test_create_one_schema(setup_local_env, yoma_agent):
    # given
    definition = SchemaDefinition(name="x", version="0.1", attributes=["average"])

    public_did = await create_public_did(yoma_agent)
    print(f" created did:{public_did}")

    # when
    schema_definition_result = await create_schema(definition, yoma_agent)
    print(schema_definition_result)

    # then
    response = await yoma_agent.schema.get_created_schema(
        schema_issuer_did=public_did["did"]
    )

    assert_that(response["schema_ids"]).contains(schema_definition_result["schema_id"])


@pytest.mark.asyncio
async def test_update_schema(setup_local_env, yoma_agent):
    # given
    definition1 = SchemaDefinition(name="xya", version="0.1", attributes=["average"])
    definition2 = SchemaDefinition(
        name="xya", version="0.2", attributes=["average", "bitrate"]
    )
    public_did = await create_public_did(yoma_agent)
    print(f" created did:{public_did}")

    # when
    schema_definition_result_1 = await create_schema(definition1, yoma_agent)
    schema_definition_result_2 = await create_schema(definition2, yoma_agent)

    # then
    response = await yoma_agent.schema.get_created_schema(
        schema_issuer_did=public_did["did"]
    )

    assert_that(response["schema_ids"]).contains_only(
        schema_definition_result_1["schema_id"],
        schema_definition_result_2["schema_id"],
    )


@pytest.mark.asyncio
async def test_create_two_schemas(setup_local_env, yoma_agent):
    # given
    definition1 = SchemaDefinition(name="x", version="0.1", attributes=["average"])
    definition2 = SchemaDefinition(name="y", version="0.1", attributes=["average"])

    public_did = await create_public_did(yoma_agent)
    print(f" created did:{public_did}")

    # when
    schema_definition_result_1 = await create_schema(definition1, yoma_agent)
    schema_definition_result_2 = await create_schema(definition2, yoma_agent)

    # then
    response = await yoma_agent.schema.get_created_schema(
        schema_issuer_did=public_did["did"]
    )

    assert_that(response["schema_ids"]).contains_only(
        schema_definition_result_1["schema_id"],
        schema_definition_result_2["schema_id"],
    )


@pytest.mark.asyncio
async def test_get_schemas(setup_local_env, yoma_agent):
    # when
    name = get_random_string(10)
    definition1 = SchemaDefinition(name=name, version="0.1", attributes=["average"])
    definition2 = SchemaDefinition(
        name=name, version="0.2", attributes=["average", "bitrate"]
    )
    public_did = await create_public_did(yoma_agent)
    print(f" created did:{public_did}")
    schema_definition_result_1 = await create_schema(definition1, yoma_agent)
    schema_definition_result_2 = await create_schema(definition2, yoma_agent)

    # when
    response = await get_schemas(
        schema_issuer_did=public_did["did"], aries_controller=yoma_agent
    )

    # then
    assert_that(response["schema_ids"]).contains_only(
        schema_definition_result_1["schema_id"],
        schema_definition_result_2["schema_id"],
    )
    # when
    response = await get_schemas(schema_name=name, aries_controller=yoma_agent)
    # then
    assert_that(response["schema_ids"]).contains_only(
        schema_definition_result_1["schema_id"],
        schema_definition_result_2["schema_id"],
    )

    # when
    response = await get_schemas(
        schema_name=name, schema_version="0.2", aries_controller=yoma_agent
    )
    # then
    assert_that(response["schema_ids"]).contains_only(
        schema_definition_result_2["schema_id"],
    )
