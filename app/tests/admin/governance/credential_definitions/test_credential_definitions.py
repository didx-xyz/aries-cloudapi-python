import pytest
from aries_cloudcontroller import AcaPyClient
from assertpy import assert_that
from httpx import AsyncClient
from app.admin.governance.credential_definitions import (
    CredentialDefinition,
    create_credential_definition,
    get_created_credential_definitions,
    get_credential_definition,
    router,
)
from app.admin.governance.schemas import SchemaDefinition, create_schema
from app.tests.admin.governance.schemas.test_schemas import create_public_did
from app.tests.util.client_fixtures import yoma_acapy_client, yoma_client
from app.tests.util.event_loop import event_loop
from app.tests.util.string import get_random_string

BASE_PATH = router.prefix


@pytest.mark.asyncio
async def test_create_credential_definition(yoma_acapy_client: AcaPyClient):
    # given
    definition = SchemaDefinition(name="x", version="0.1", attributes=["average"])

    public_did = await create_public_did(yoma_acapy_client)
    schema_definition_result = (
        await create_schema(definition, yoma_acapy_client)
    ).dict()

    credential_definition = CredentialDefinition(
        schema_id=schema_definition_result["schema_id"],
        tag=get_random_string(5),
        support_revocation=False,
    )

    # when
    result = (
        await create_credential_definition(credential_definition, yoma_acapy_client)
    ).dict()

    # then
    written = (
        await get_credential_definition(
            result["credential_definition_id"], yoma_acapy_client
        )
    ).dict()
    assert_that(written).is_not_empty().contains_key("credential_definition")
    assert_that(written["credential_definition"]["tag"]).is_equal_to(
        credential_definition.tag
    )


@pytest.mark.asyncio
async def test_create_credential_definition_via_web(
    yoma_client: AsyncClient, yoma_acapy_client: AcaPyClient
):
    # given
    definition = SchemaDefinition(name="x", version="0.1", attributes=["average"])

    public_did = await create_public_did(yoma_acapy_client)
    schema_definition_result = (
        await create_schema(definition, yoma_acapy_client)
    ).dict()

    credential_definition = CredentialDefinition(
        schema_id=schema_definition_result["schema_id"],
        tag=get_random_string(5),
        support_revocation=False,
    )

    # when
    result = (
        await yoma_client.post(BASE_PATH, json=credential_definition.dict())
    ).json()

    # then
    written = (
        await get_credential_definition(
            result["credential_definition_id"], yoma_acapy_client
        )
    ).dict()
    assert_that(written).is_not_empty().contains_key("credential_definition")
    assert_that(written["credential_definition"]["tag"]).is_equal_to(
        credential_definition.tag
    )


@pytest.mark.asyncio
async def test_get_credential_definitions(yoma_acapy_client: AcaPyClient):
    # given
    definition1 = SchemaDefinition(name="x", version="0.1", attributes=["average"])
    definition2 = SchemaDefinition(name="y", version="0.1", attributes=["average"])

    public_did = await create_public_did(yoma_acapy_client)
    schema_definition_result_1 = (
        await create_schema(definition1, yoma_acapy_client)
    ).dict()
    schema_definition_result_2 = (
        await create_schema(definition2, yoma_acapy_client)
    ).dict()

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

    await create_credential_definition(credential_definition_1, yoma_acapy_client)
    credential_definition_result_2 = (
        await create_credential_definition(credential_definition_2, yoma_acapy_client)
    ).dict()

    # when
    credential_definition = (
        await get_created_credential_definitions(
            schema_id=schema_definition_result_2["schema_id"],
            aries_controller=yoma_acapy_client,
        )
    ).dict()

    # then
    assert_that(credential_definition["credential_definition_ids"]).contains_only(
        credential_definition_result_2["credential_definition_id"]
    )


@pytest.mark.asyncio
async def test_get_credential_definitions_via_web(
    yoma_client: AsyncClient, yoma_acapy_client: AcaPyClient
):
    # given
    definition = SchemaDefinition(name="x", version="0.1", attributes=["average"])

    public_did = await create_public_did(yoma_acapy_client)
    schema_definition_result = (
        await create_schema(definition, yoma_acapy_client)
    ).dict()

    credential_definition = CredentialDefinition(
        schema_id=schema_definition_result["schema_id"],
        tag="tag",
        support_revocation=False,
    )

    credential_definition_result = (
        await create_credential_definition(credential_definition, yoma_acapy_client)
    ).dict()

    # when
    credential_definition = (
        await yoma_client.get(
            f"{BASE_PATH}/created",
            params={"schema_id": schema_definition_result["schema_id"]},
        )
    ).json()

    # then
    assert_that(credential_definition["credential_definition_ids"]).contains_only(
        credential_definition_result["credential_definition_id"]
    )


@pytest.mark.asyncio
async def test_get_credential_definition(yoma_acapy_client: AcaPyClient):
    # given
    definition1 = SchemaDefinition(name="x", version="0.1", attributes=["average"])

    await create_public_did(yoma_acapy_client)
    schema_definition_result_1 = (
        await create_schema(definition1, yoma_acapy_client)
    ).dict()

    credential_definition_1 = CredentialDefinition(
        schema_id=schema_definition_result_1["schema_id"],
        tag=get_random_string(5),
        support_revocation=False,
    )

    credential_definition_result = (
        await create_credential_definition(credential_definition_1, yoma_acapy_client)
    ).dict()

    # when
    result = (
        await get_credential_definition(
            credential_definition_result["credential_definition_id"], yoma_acapy_client
        )
    ).dict()

    # then
    assert_that(result).contains_key("credential_definition")
    assert_that(result["credential_definition"]).is_not_none()
    assert_that(result["credential_definition"]["tag"]).is_equal_to(
        credential_definition_1.tag
    )


@pytest.mark.asyncio
async def test_get_credential_definition_via_web(
    yoma_client: AsyncClient, yoma_acapy_client: AcaPyClient
):
    # given
    definition1 = SchemaDefinition(name="x", version="0.1", attributes=["average"])
    await create_public_did(yoma_acapy_client)
    schema_definition_result_1 = (
        await create_schema(definition1, yoma_acapy_client)
    ).dict()
    credential_definition_1 = CredentialDefinition(
        schema_id=schema_definition_result_1["schema_id"],
        tag=get_random_string(5),
        support_revocation=False,
    )
    credential_definition_result = (
        await create_credential_definition(credential_definition_1, yoma_acapy_client)
    ).dict()
    # when
    result_json = (
        await yoma_client.get(
            f"{BASE_PATH}/{credential_definition_result['credential_definition_id']}"
        )
    ).json()
    # then
    assert_that(result_json).contains_key("credential_definition")
    assert_that(result_json["credential_definition"]).is_not_none()
    assert_that(result_json["credential_definition"]["tag"]).is_equal_to(
        credential_definition_1.tag
    )
