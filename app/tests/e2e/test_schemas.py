import pytest
from aries_cloudcontroller import AcaPyClient
from assertpy import assert_that
from fastapi.exceptions import HTTPException
from httpx import AsyncClient

from app.admin.schemas import (
    SchemaDefinition,
    create_schema,
    get_schemas,
    get_schemas_list_detailed,
    router,
    update_schema,
)
from app.tests.util.ledger import create_public_did

# These imports are important for tests to run!
from app.tests.util.event_loop import event_loop
from app.tests.util.string import get_random_string

BASE_PATH = router.prefix


@pytest.mark.asyncio
async def test_create_schema_via_web(
    yoma_client: AsyncClient, yoma_acapy_client: AcaPyClient
):
    definition = SchemaDefinition(name="x", version="0.1", attributes=["average"])

    await create_public_did(yoma_acapy_client)

    response = await yoma_client.post(BASE_PATH, json=definition.dict())
    assert response.status_code == 200
    result = response.json()

    response = await get_schemas(
        schema_id=result["schema_id"], aries_controller=yoma_acapy_client
    )
    assert_that(response.schema_ids).is_length(1)


@pytest.mark.asyncio
async def test_get_schemas_via_web(
    yoma_client: AsyncClient, yoma_acapy_client: AcaPyClient
):
    # given
    definition = SchemaDefinition(name="x", version="0.1", attributes=["average"])
    await create_public_did(yoma_acapy_client)

    # when
    response = await yoma_client.post(BASE_PATH, json=definition.dict())
    assert response.status_code == 200
    result = response.json()

    # then
    response = await yoma_client.get(
        BASE_PATH,
        params={"schema_id": result["schema_id"]},
    )
    assert_that(response.json()["schema_ids"]).is_length(1)


@pytest.mark.asyncio
async def test_get_schema_via_web(
    yoma_client: AsyncClient, yoma_acapy_client: AcaPyClient
):
    # given
    definition = SchemaDefinition(name="x", version="0.1", attributes=["average"])

    await create_public_did(yoma_acapy_client)
    response = await yoma_client.post(
        "/admin/governance/schemas",
        json=definition.dict(),
    )
    assert response.status_code == 200
    result = response.json()

    # when
    response = await yoma_client.get(
        f"{BASE_PATH}/{result['schema_id']}",
    )

    # then
    assert_that(response.json()["schema"]["attrNames"]).contains_only("average")


@pytest.mark.asyncio
async def test_create_one_schema(yoma_acapy_client: AcaPyClient):
    # given
    definition = SchemaDefinition(name="x", version="0.1", attributes=["average"])

    public_did = await create_public_did(yoma_acapy_client)

    # when
    schema_definition_result = await create_schema(definition, yoma_acapy_client)

    # then
    response = await yoma_acapy_client.schema.get_created_schemas(
        schema_issuer_did=public_did.did
    )

    assert_that(response.dict()["schema_ids"]).contains(
        schema_definition_result.schema_id
    )


@pytest.mark.asyncio
async def test_update_schemas(yoma_acapy_client: AcaPyClient):
    # given
    definition1 = SchemaDefinition(name="xya", version="0.1", attributes=["average"])
    definition2 = SchemaDefinition(
        name="xya", version="0.2", attributes=["average", "bitrate"]
    )
    public_did = await create_public_did(yoma_acapy_client)

    # when
    schema_definition_result_1 = await create_schema(definition1, yoma_acapy_client)
    schema_definition_result_2 = await create_schema(definition2, yoma_acapy_client)

    # then
    response = await yoma_acapy_client.schema.get_created_schemas(
        schema_issuer_did=public_did.did
    )

    assert_that(response.dict()["schema_ids"]).contains_only(
        schema_definition_result_1.schema_id,
        schema_definition_result_2.schema_id,
    )


@pytest.mark.asyncio
async def test_create_two_schemas(yoma_acapy_client: AcaPyClient):
    # given
    definition1 = SchemaDefinition(name="x", version="0.1", attributes=["average"])
    definition2 = SchemaDefinition(name="y", version="0.1", attributes=["average"])

    public_did = await create_public_did(yoma_acapy_client)

    # when
    schema_definition_result_1 = await create_schema(definition1, yoma_acapy_client)
    schema_definition_result_2 = await create_schema(definition2, yoma_acapy_client)

    # then
    response = await yoma_acapy_client.schema.get_created_schemas(
        schema_issuer_did=public_did.did
    )

    assert_that(response.dict()["schema_ids"]).contains_only(
        schema_definition_result_1.schema_id,
        schema_definition_result_2.schema_id,
    )


@pytest.mark.asyncio
async def test_get_schemas(yoma_acapy_client: AcaPyClient):
    # when
    name = get_random_string(10)
    definition1 = SchemaDefinition(name=name, version="0.1", attributes=["average"])
    definition2 = SchemaDefinition(
        name=name, version="0.2", attributes=["average", "bitrate"]
    )
    public_did = await create_public_did(yoma_acapy_client)

    schema_definition_result_1 = await create_schema(definition1, yoma_acapy_client)
    schema_definition_result_2 = await create_schema(definition2, yoma_acapy_client)

    # when
    response = await get_schemas(
        schema_issuer_did=public_did.did, aries_controller=yoma_acapy_client
    )

    # then
    assert_that(response.dict()["schema_ids"]).contains_only(
        schema_definition_result_1.schema_id,
        schema_definition_result_2.schema_id,
    )
    # when
    response = await get_schemas(schema_name=name, aries_controller=yoma_acapy_client)
    # then
    assert_that(response.dict()["schema_ids"]).contains_only(
        schema_definition_result_1.schema_id,
        schema_definition_result_2.schema_id,
    )

    # when
    response = await get_schemas(
        schema_name=name, schema_version="0.2", aries_controller=yoma_acapy_client
    )
    # then
    assert_that(response.dict()["schema_ids"]).contains_only(
        schema_definition_result_2.schema_id,
    )


@pytest.mark.asyncio
async def test_get_schemas_detail_list(yoma_acapy_client: AcaPyClient):
    name = get_random_string(10)
    definition1 = SchemaDefinition(name=name, version="0.1", attributes=["average"])
    definition2 = SchemaDefinition(
        name=name, version="0.2", attributes=["average", "bitrate"]
    )
    public_did = await create_public_did(yoma_acapy_client)

    schema_definition_result_1 = await create_schema(definition1, yoma_acapy_client)
    schema_definition_result_2 = await create_schema(definition2, yoma_acapy_client)

    response = await get_schemas_list_detailed(
        schema_issuer_did=public_did.did, aries_controller=yoma_acapy_client
    )

    assert response
    assert schema_definition_result_1.schema_id in response
    assert schema_definition_result_2.schema_id in response
    assert [
        k in response[schema_definition_result_1.schema_id].keys()
        for k in ["name", "version", "attributes"]
    ]

    response = await get_schemas_list_detailed(
        schema_name=name, aries_controller=yoma_acapy_client
    )

    assert response
    assert schema_definition_result_1.schema_id in response
    assert schema_definition_result_2.schema_id in response

    response = await get_schemas_list_detailed(
        schema_name=name, schema_version="0.2", aries_controller=yoma_acapy_client
    )
    assert schema_definition_result_2.schema_id in response


@pytest.mark.asyncio
async def test_update_schema(yoma_acapy_client: AcaPyClient):
    name = get_random_string(10)
    definition = SchemaDefinition(name=name, version="0.1", attributes=["average"])

    public_did = await create_public_did(yoma_acapy_client)

    schema_definition_result = await create_schema(definition, yoma_acapy_client)
    definition_updated = SchemaDefinition(
        name=name, version="0.2", attributes=["average"]
    )
    updated_result = await update_schema(
        schema_id=schema_definition_result.schema_id,
        schema_definition=definition_updated,
        aries_controller=yoma_acapy_client,
    )

    response = (
        await get_schemas(
            schema_issuer_did=public_did.did, aries_controller=yoma_acapy_client
        )
    ).dict()

    assert updated_result
    assert updated_result.schema_.id in response["schema_ids"]

    definition_updated_low = SchemaDefinition(
        name=name, version="0.0", attributes=["average"]
    )

    with pytest.raises(HTTPException) as exc:
        await update_schema(
            schema_id=schema_definition_result.schema_id,
            schema_definition=definition_updated_low,
            aries_controller=yoma_acapy_client,
        )
    assert exc.value.status_code == 405
    assert "Updated version must be higher than" in exc.value.detail
