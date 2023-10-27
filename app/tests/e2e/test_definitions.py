import pytest
from aries_cloudcontroller import AcaPyClient
from assertpy import assert_that

from app.dependencies.auth import AcaPyAuthVerified, acapy_auth, acapy_auth_verified
from app.routes import definitions
from app.routes.definitions import (
    CreateCredentialDefinition,
    CreateSchema,
    CredentialSchema,
)
from app.services.acapy_wallet import get_public_did
from app.services.trust_registry.util.schema import registry_has_schema
from app.tests.util.trust_registry import register_issuer
from app.util.string import random_string
from shared import RichAsyncClient


@pytest.mark.anyio
async def test_create_credential_definition(mock_governance_auth: AcaPyAuthVerified):
    # given
    schema = CreateSchema(
        name=random_string(15), version="0.1", attribute_names=["average"]
    )

    schema_result = (
        await definitions.create_schema(schema, mock_governance_auth)
    ).model_dump()
    schema_id = schema_result["id"]

    credential_definition = CreateCredentialDefinition(
        schema_id=schema_id, tag=random_string(5), support_revocation=True
    )

    # when
    result = (
        await definitions.create_credential_definition(
            credential_definition, mock_governance_auth
        )
    ).model_dump()

    assert_that(result).has_tag(credential_definition.tag)
    assert_that(result).has_schema_id(credential_definition.schema_id)
    assert_that(result["id"]).is_not_empty()


@pytest.mark.anyio
async def test_create_schema(
    governance_public_did: str, mock_governance_auth: AcaPyAuthVerified
):
    # given
    send = CreateSchema(
        name=random_string(15), version="0.1", attribute_names=["average"]
    )

    result = (await definitions.create_schema(send, mock_governance_auth)).model_dump()

    # Assert schemas has been registered in the trust registry
    assert await registry_has_schema(result["id"])
    expected_schema = f"{governance_public_did}:2:{send.name}:{send.version}"
    assert_that(result).has_id(expected_schema)
    assert_that(result).has_name(send.name)
    assert_that(result).has_version(send.version)
    assert_that(result).has_attribute_names(send.attribute_names)


@pytest.mark.anyio
async def test_get_schema(
    governance_public_did: str, mock_governance_auth: AcaPyAuthVerified
):
    # given
    schema = CreateSchema(
        name=random_string(15), version="0.1", attribute_names=["average"]
    )

    create_result = (
        await definitions.create_schema(schema, mock_governance_auth)
    ).model_dump()
    result = await definitions.get_schema(create_result["id"], mock_governance_auth)

    assert await registry_has_schema(result.id)
    expected_schema = f"{governance_public_did}:2:{schema.name}:{schema.version}"
    assert_that(result).has_id(expected_schema)
    assert_that(result).has_name(schema.name)
    assert_that(result).has_version(schema.version)
    assert_that(result).has_attribute_names(schema.attribute_names)


@pytest.mark.anyio
async def test_get_credential_definition(
    governance_client: RichAsyncClient, mock_governance_auth: AcaPyAuthVerified
):
    # given
    schema_send = CreateSchema(
        name=random_string(15), version="0.1", attribute_names=["average"]
    )

    schema_result = (
        await definitions.create_schema(schema_send, mock_governance_auth)
    ).model_dump()

    await register_issuer(governance_client, schema_result["id"])
    credential_definition = CreateCredentialDefinition(
        schema_id=schema_result["id"], tag=random_string(5)
    )

    # when
    create_result = (
        await definitions.create_credential_definition(
            credential_definition, mock_governance_auth
        )
    ).model_dump()

    result = (
        await definitions.get_credential_definition_by_id(
            create_result["id"], mock_governance_auth
        )
    ).model_dump()

    assert_that(result).has_tag(credential_definition.tag)
    assert_that(result).has_schema_id(credential_definition.schema_id)
    assert_that(result["id"]).is_not_empty()


@pytest.mark.anyio
async def test_create_credential_definition_issuer_tenant(
    schema_definition: CredentialSchema,
    faber_acapy_client: AcaPyClient,
    faber_client: RichAsyncClient,
):
    credential_definition = CreateCredentialDefinition(
        schema_id=schema_definition.id,
        tag=random_string(5),
        support_revocation=True,
    )

    auth = acapy_auth_verified(acapy_auth(faber_client.headers["x-api-key"]))

    result = (
        await definitions.create_credential_definition(credential_definition, auth)
    ).model_dump()

    faber_public_did = await get_public_did(faber_acapy_client)
    schema = await faber_acapy_client.schema.get_schema(schema_id=schema_definition.id)

    assert_that(result).has_id(
        f"{faber_public_did.did}:3:CL:{schema.var_schema.seq_no}:{credential_definition.tag}"
    )
    assert_that(result).has_tag(credential_definition.tag)
