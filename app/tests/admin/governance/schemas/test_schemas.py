import random

import string

from contextlib import asynccontextmanager, contextmanager

import json

import pytest
from assertpy import assert_that
from httpx import AsyncClient

import acapy_ledger_facade
import acapy_wallet_facade
import facade
import ledger_facade
import utils
from admin.governance.schemas import SchemaDefinition, create_schema, get_schemas
from facade import create_yoma_controller
from main import app

# want to wrap an existing method with a decorator
# the method is normally used by fast api and then fast api manages the tear down
get_yoma_agent = asynccontextmanager(create_yoma_controller)


@pytest.fixture
def setup_local_env():
    utils.is_multitenant = False
    utils.yoma_agent_url = "http://localhost:3021"
    ledger_facade.LEDGER_TYPE = "von"


@pytest.mark.asyncio
async def test_create_schema_via_web(setup_local_env, async_client):
    definition = SchemaDefinition(name="x", version="0.1", attributes=["average"])

    async with get_yoma_agent(x_api_key="adminApiKey") as controller:
        public_did = await create_public_did(controller)

        response = await async_client.post(
            "/admin/governance/schemas",
            data=json.dumps(definition.dict()),
            headers={"x-api-key": "adminApiKey", "content-type": "application/json"},
        )
        assert response.status_code == 200
        result = response.json()

        response = await get_schemas(
            schema_id=result["schema_id"], aries_controller=controller
        )
        assert_that(response["schema_ids"]).is_length(1)


@pytest.mark.asyncio
async def test_get_schemas_via_web(setup_local_env, async_client):
    definition = SchemaDefinition(name="x", version="0.1", attributes=["average"])

    async with get_yoma_agent(x_api_key="adminApiKey") as controller:
        public_did = await create_public_did(controller)
        response = await async_client.post(
            "/admin/governance/schemas",
            data=json.dumps(definition.dict()),
            headers={"x-api-key": "adminApiKey", "content-type": "application/json"},
        )
        assert response.status_code == 200
        result = response.json()

        response = await async_client.get(
            "/admin/governance/schemas",
            params={"schema_id": result["schema_id"]},
            headers={"x-api-key": "adminApiKey", "content-type": "application/json"},
        )
        assert_that(response.json()["schema_ids"]).is_length(1)


@pytest.mark.asyncio
async def test_get_schema_via_web(setup_local_env, async_client):
    definition = SchemaDefinition(name="x", version="0.1", attributes=["average"])

    async with get_yoma_agent(x_api_key="adminApiKey") as controller:
        public_did = await create_public_did(controller)
        response = await async_client.post(
            "/admin/governance/schemas",
            data=json.dumps(definition.dict()),
            headers={"x-api-key": "adminApiKey", "content-type": "application/json"},
        )
        assert response.status_code == 200
        result = response.json()

        response = await async_client.get(
            f"/admin/governance/schemas/{result['schema_id']}",
            headers={"x-api-key": "adminApiKey", "content-type": "application/json"},
        )
        assert_that(response.json()["schema"]["attrNames"]).contains_only("average")


async def create_public_did(aries_agent_controller):
    generate_did_res = await acapy_wallet_facade.create_did(aries_agent_controller)
    did_object = generate_did_res["result"]
    await ledger_facade.post_to_ledger(
        did_object=did_object, ledger_url="http://localhost:9000/register"
    )
    # my local von network I was using did not requried the TAA
    # taa_response = await acapy_ledger_facade.get_taa(aries_agent_controller)
    # await acapy_ledger_facade.accept_taa(aries_agent_controller, taa_response)
    await acapy_wallet_facade.assign_pub_did(aries_agent_controller, did_object["did"])
    return did_object


@pytest.mark.asyncio
async def test_create_one_schema(setup_local_env):
    definition = SchemaDefinition(name="x", version="0.1", attributes=["average"])

    async with get_yoma_agent(x_api_key="adminApiKey") as controller:
        public_did = await create_public_did(controller)
        print(f" created did:{public_did}")
        schema_definition_result = await create_schema(definition, controller)
        print(schema_definition_result)

        response = await controller.schema.get_created_schema(
            schema_issuer_did=public_did["did"]
        )

        assert_that(response["schema_ids"]).contains(
            schema_definition_result["schema_id"]
        )


@pytest.mark.asyncio
async def test_update_schema(setup_local_env):
    definition1 = SchemaDefinition(name="xya", version="0.1", attributes=["average"])
    definition2 = SchemaDefinition(
        name="xya", version="0.2", attributes=["average", "bitrate"]
    )
    # definition.name = 'x'
    # definition.version = '1'
    # definition.attributes = ['name']

    async with get_yoma_agent(x_api_key="adminApiKey") as controller:
        public_did = await create_public_did(controller)
        print(f" created did:{public_did}")
        schema_definition_result_1 = await create_schema(definition1, controller)
        schema_definition_result_2 = await create_schema(definition2, controller)

        response = await controller.schema.get_created_schema(
            schema_issuer_did=public_did["did"]
        )

        assert_that(response["schema_ids"]).contains_only(
            schema_definition_result_1["schema_id"],
            schema_definition_result_2["schema_id"],
        )


@pytest.mark.asyncio
async def test_create_two_schemas(setup_local_env):
    definition1 = SchemaDefinition(name="x", version="0.1", attributes=["average"])
    definition2 = SchemaDefinition(name="y", version="0.1", attributes=["average"])

    async with get_yoma_agent(x_api_key="adminApiKey") as controller:
        public_did = await create_public_did(controller)
        print(f" created did:{public_did}")
        schema_definition_result_1 = await create_schema(definition1, controller)
        schema_definition_result_2 = await create_schema(definition2, controller)

        response = await controller.schema.get_created_schema(
            schema_issuer_did=public_did["did"]
        )

        assert_that(response["schema_ids"]).contains_only(
            schema_definition_result_1["schema_id"],
            schema_definition_result_2["schema_id"],
        )


def get_random_name():
    letters = string.ascii_uppercase
    return "".join(random.choice(letters) for i in range(10))


@pytest.mark.asyncio
async def test_get_schemas(setup_local_env):
    name = get_random_name()
    definition1 = SchemaDefinition(name=name, version="0.1", attributes=["average"])
    definition2 = SchemaDefinition(
        name=name, version="0.2", attributes=["average", "bitrate"]
    )
    # definition.name = 'x'
    # definition.version = '1'
    # definition.attributes = ['name']

    async with get_yoma_agent(x_api_key="adminApiKey") as controller:
        public_did = await create_public_did(controller)
        print(f" created did:{public_did}")
        schema_definition_result_1 = await create_schema(definition1, controller)
        schema_definition_result_2 = await create_schema(definition2, controller)

        response = await get_schemas(
            schema_issuer_did=public_did["did"], aries_controller=controller
        )
        assert_that(response["schema_ids"]).contains_only(
            schema_definition_result_1["schema_id"],
            schema_definition_result_2["schema_id"],
        )
        response = await get_schemas(schema_name=name, aries_controller=controller)
        assert_that(response["schema_ids"]).contains_only(
            schema_definition_result_1["schema_id"],
            schema_definition_result_2["schema_id"],
        )

        response = await get_schemas(
            schema_name=name, schema_version="0.2", aries_controller=controller
        )
        assert_that(response["schema_ids"]).contains_only(
            schema_definition_result_2["schema_id"],
        )
