import pytest
from aries_cloudcontroller import AcaPyClient
from assertpy import assert_that
from httpx import AsyncClient

from app.admin.schemas import (
    SchemaDefinition,
    create_schema,
    get_schemas,
    router,
)
from app.tests.util.ledger import create_public_did
from app.facades import trust_registry

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

    # Assert schemas has been registered in the trust registry
    assert await trust_registry.registry_has_schema(schema_definition_result.schema_id)


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

    # Assert schemas have been registered in the trust registry
    assert await trust_registry.registry_has_schema(
        schema_definition_result_1.schema_id
    )
    assert await trust_registry.registry_has_schema(
        schema_definition_result_2.schema_id
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
