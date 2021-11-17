import json

import pytest
from assertpy import assert_that
from fastapi.exceptions import HTTPException

import app.facades.ledger as ledger_facade
import app.utils as utils
from app.facades.acapy_ledger import create_pub_did as create_public_did
from app.admin.governance.schemas import (
    SchemaDefinition,
    create_schema,
    get_schemas,
    get_schemas_list_detailed,
    update_schema,
    router,
)

# want to wrap an existing method with a decorator
# the method is normally used by fast api and then fast api manages the tear down
from app.tests.utils_test import get_random_string

APPLICATION_JSON_CONTENT_TYPE = {"content-type": "application/json"}
BASE_PATH = router.prefix


@pytest.fixture
def setup_local_env():
    utils.is_multitenant = False
    ledger_facade.LEDGER_TYPE = "von"


@pytest.mark.asyncio
async def test_create_schema_via_web(setup_local_env, async_client, yoma_agent_mock):
    definition = SchemaDefinition(name="x", version="0.1", attributes=["average"])

    await create_public_did(yoma_agent_mock)

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
    assert_that(response.dict()["schema_ids"]).is_length(1)


@pytest.mark.asyncio
async def test_get_schemas_via_web(setup_local_env, async_client, yoma_agent_mock):
    # given
    definition = SchemaDefinition(name="x", version="0.1", attributes=["average"])

    await create_public_did(yoma_agent_mock)

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
async def test_get_schema_via_web(setup_local_env, async_client, yoma_agent_mock):
    # given
    definition = SchemaDefinition(name="x", version="0.1", attributes=["average"])

    await create_public_did(yoma_agent_mock)
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
async def test_create_one_schema(setup_local_env, yoma_agent_mock):
    # given
    definition = SchemaDefinition(name="x", version="0.1", attributes=["average"])

    public_did = (await create_public_did(yoma_agent_mock)).dict()["did_object"]
    print(f" created did:{public_did}")

    # when
    schema_definition_result = (await create_schema(definition, yoma_agent_mock)).dict()
    print(schema_definition_result)

    # then
    response = await yoma_agent_mock.schema.get_created_schemas(
        schema_issuer_did=public_did["did"]
    )

    assert_that(response.dict()["schema_ids"]).contains(
        schema_definition_result["schema_id"]
    )


@pytest.mark.asyncio
async def test_update_schemas(setup_local_env, yoma_agent_mock):
    # given
    definition1 = SchemaDefinition(name="xya", version="0.1", attributes=["average"])
    definition2 = SchemaDefinition(
        name="xya", version="0.2", attributes=["average", "bitrate"]
    )
    public_did = (await create_public_did(yoma_agent_mock)).dict()["did_object"]
    print(f" created did:{public_did}")

    # when
    schema_definition_result_1 = (
        await create_schema(definition1, yoma_agent_mock)
    ).dict()
    schema_definition_result_2 = (
        await create_schema(definition2, yoma_agent_mock)
    ).dict()

    # then
    response = await yoma_agent_mock.schema.get_created_schemas(
        schema_issuer_did=public_did["did"]
    )

    assert_that(response.dict()["schema_ids"]).contains_only(
        schema_definition_result_1["schema_id"],
        schema_definition_result_2["schema_id"],
    )


@pytest.mark.asyncio
async def test_create_two_schemas(setup_local_env, yoma_agent_mock):
    # given
    definition1 = SchemaDefinition(name="x", version="0.1", attributes=["average"])
    definition2 = SchemaDefinition(name="y", version="0.1", attributes=["average"])

    public_did = (await create_public_did(yoma_agent_mock)).dict()["did_object"]
    print(f" created did:{public_did}")

    # when
    schema_definition_result_1 = (
        await create_schema(definition1, yoma_agent_mock)
    ).dict()
    schema_definition_result_2 = (
        await create_schema(definition2, yoma_agent_mock)
    ).dict()

    # then
    response = await yoma_agent_mock.schema.get_created_schemas(
        schema_issuer_did=public_did["did"]
    )

    assert_that(response.dict()["schema_ids"]).contains_only(
        schema_definition_result_1["schema_id"],
        schema_definition_result_2["schema_id"],
    )


@pytest.mark.asyncio
async def test_get_schemas(setup_local_env, yoma_agent_mock):
    # when
    name = get_random_string(10)
    definition1 = SchemaDefinition(name=name, version="0.1", attributes=["average"])
    definition2 = SchemaDefinition(
        name=name, version="0.2", attributes=["average", "bitrate"]
    )
    public_did = (await create_public_did(yoma_agent_mock)).dict()["did_object"]
    print(f" created did:{public_did}")
    schema_definition_result_1 = (
        await create_schema(definition1, yoma_agent_mock)
    ).dict()
    schema_definition_result_2 = (
        await create_schema(definition2, yoma_agent_mock)
    ).dict()

    # when
    response = await get_schemas(
        schema_issuer_did=public_did["did"], aries_controller=yoma_agent_mock
    )

    # then
    assert_that(response.dict()["schema_ids"]).contains_only(
        schema_definition_result_1["schema_id"],
        schema_definition_result_2["schema_id"],
    )
    # when
    response = await get_schemas(schema_name=name, aries_controller=yoma_agent_mock)
    # then
    assert_that(response.dict()["schema_ids"]).contains_only(
        schema_definition_result_1["schema_id"],
        schema_definition_result_2["schema_id"],
    )

    # when
    response = await get_schemas(
        schema_name=name, schema_version="0.2", aries_controller=yoma_agent_mock
    )
    # then
    assert_that(response.dict()["schema_ids"]).contains_only(
        schema_definition_result_2["schema_id"],
    )


@pytest.mark.asyncio
async def test_get_schemas_detail_list(setup_local_env, yoma_agent_mock):
    name = get_random_string(10)
    definition1 = SchemaDefinition(name=name, version="0.1", attributes=["average"])
    definition2 = SchemaDefinition(
        name=name, version="0.2", attributes=["average", "bitrate"]
    )
    public_did = (await create_public_did(yoma_agent_mock)).dict()["did_object"]
    print(f" created did:{public_did}")
    schema_definition_result_1 = (
        await create_schema(definition1, yoma_agent_mock)
    ).dict()
    schema_definition_result_2 = (
        await create_schema(definition2, yoma_agent_mock)
    ).dict()

    response = await get_schemas_list_detailed(
        schema_issuer_did=public_did["did"], aries_controller=yoma_agent_mock
    )

    assert response
    assert schema_definition_result_1["schema_id"] in response
    assert schema_definition_result_2["schema_id"] in response
    assert [
        k in response[schema_definition_result_1["schema_id"]].keys()
        for k in ["name", "version", "attributes"]
    ]

    response = await get_schemas_list_detailed(
        schema_name=name, aries_controller=yoma_agent_mock
    )

    assert response
    assert schema_definition_result_1["schema_id"] in response
    assert schema_definition_result_2["schema_id"] in response

    response = await get_schemas_list_detailed(
        schema_name=name, schema_version="0.2", aries_controller=yoma_agent_mock
    )
    assert schema_definition_result_2["schema_id"] in response


@pytest.mark.asyncio
async def test_update_schema(setup_local_env, yoma_agent_mock):
    name = get_random_string(10)
    definition = SchemaDefinition(name=name, version="0.1", attributes=["average"])

    public_did = (await create_public_did(yoma_agent_mock)).dict()["did_object"]
    print(f" created did:{public_did}")

    schema_definition_result = (await create_schema(definition, yoma_agent_mock)).dict()
    definition_updated = SchemaDefinition(
        name=name, version="0.2", attributes=["average"]
    )
    updated_result = await update_schema(
        schema_id=schema_definition_result["schema_id"],
        schema_definition=definition_updated,
        aries_controller=yoma_agent_mock,
    )

    response = (
        await get_schemas(
            schema_issuer_did=public_did["did"], aries_controller=yoma_agent_mock
        )
    ).dict()

    assert updated_result
    assert updated_result["id"] in response["schema_ids"]

    definition_updated_low = SchemaDefinition(
        name=name, version="0.0", attributes=["average"]
    )

    with pytest.raises(HTTPException) as exc:
        await update_schema(
            schema_id=schema_definition_result["schema_id"],
            schema_definition=definition_updated_low,
            aries_controller=yoma_agent_mock,
        )
    assert exc.value.status_code == 405
    assert "pdated version must be higher than" in exc.value.detail
