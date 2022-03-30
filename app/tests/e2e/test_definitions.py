from httpx import AsyncClient
import pytest
import asyncio
from aries_cloudcontroller import AcaPyClient
from assertpy import assert_that
from app.dependencies import acapy_auth, acapy_auth_verified
from app.facades.acapy_wallet import get_public_did

from app.generic import definitions
from app.generic.definitions import (
    CreateSchema,
    CreateCredentialDefinition,
    CredentialSchema,
)
from app.tests.e2e.test_fixtures import *  # NOQA

from app.tests.util.ledger import create_public_did
from app.tests.util.string import get_random_string
from app.tests.util.trust_registry import register_issuer

# Tests are broken if we import the event_loop...
@pytest.yield_fixture(scope="session")
def event_loop(request):
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
async def test_create_credential_definition(
    yoma_acapy_client: AcaPyClient, yoma_client: AsyncClient
):
    # given
    schema_send = CreateSchema(
        name=get_random_string(15), version="0.1", attribute_names=["average"]
    )

    if not await has_public_did(yoma_acapy_client):
        await create_public_did(yoma_acapy_client, set_public=True)

    schema_result = (
        await definitions.create_schema(schema_send, yoma_acapy_client)
    ).dict()

    await register_issuer(yoma_client, schema_result["id"])

    credential_definition = CreateCredentialDefinition(
        schema_id=schema_result["id"], tag=get_random_string(5)
    )

    auth = acapy_auth_verified(acapy_auth(yoma_client.headers["x-api-key"]))

    # when
    result = (
        await definitions.create_credential_definition(
            credential_definition, yoma_acapy_client, auth
        )
    ).dict()

    assert_that(result).has_tag(credential_definition.tag)
    # FIXME: schema_is is seq_no. Should update to schema id instead
    # assert_that(result).has_schema_id(credential_definition.schema_id)
    assert_that(result["id"]).is_not_empty()


@pytest.mark.asyncio
async def test_create_schema(yoma_acapy_client: AcaPyClient):
    # given
    schema_send = CreateSchema(
        name=get_random_string(15), version="0.1", attribute_names=["average"]
    )

    if not await has_public_did(yoma_acapy_client):
        await create_public_did(yoma_acapy_client, set_public=True)
    result = (await definitions.create_schema(schema_send, yoma_acapy_client)).dict()

    assert_that(result).has_id(f"{did.did}:2:{schema_send.name}:{schema_send.version}")
    assert_that(result).has_name(schema_send.name)
    assert_that(result).has_version(schema_send.version)
    assert_that(result).has_attribute_names(schema_send.attribute_names)


@pytest.mark.asyncio
async def test_get_schema(yoma_acapy_client: AcaPyClient):
    # given
    schema_send = CreateSchema(
        name=get_random_string(15), version="0.1", attribute_names=["average"]
    )

    if not await has_public_did(yoma_acapy_client):
        await create_public_did(yoma_acapy_client, set_public=True)
    create_result = (
        await definitions.create_schema(schema_send, yoma_acapy_client)
    ).dict()
    result = await definitions.get_schema(create_result["id"], yoma_acapy_client)

    assert_that(result).has_id(f"{did.did}:2:{schema_send.name}:{schema_send.version}")
    assert_that(result).has_name(schema_send.name)
    assert_that(result).has_version(schema_send.version)
    assert_that(result).has_attribute_names(schema_send.attribute_names)


@pytest.mark.asyncio
async def test_get_credential_definition(
    yoma_acapy_client: AcaPyClient, yoma_client: AsyncClient
):
    # given
    schema_send = CreateSchema(
        name=get_random_string(15), version="0.1", attribute_names=["average"]
    )

    if not await has_public_did(yoma_acapy_client):
        await create_public_did(yoma_acapy_client, set_public=True)
    schema_result = (
        await definitions.create_schema(schema_send, yoma_acapy_client)
    ).dict()

    await register_issuer(yoma_client, schema_result["id"])
    credential_definition = CreateCredentialDefinition(
        schema_id=schema_result["id"], tag=get_random_string(5)
    )

    auth = acapy_auth_verified(acapy_auth(yoma_client.headers["x-api-key"]))

    # when
    create_result = (
        await definitions.create_credential_definition(
            credential_definition, yoma_acapy_client, auth
        )
    ).dict()

    result = (
        await definitions.get_credential_definition_by_id(
            create_result["id"], yoma_acapy_client
        )
    ).dict()

    assert_that(result).has_tag(credential_definition.tag)
    # FIXME: schema_is is seq_no. Should update to schema id instead
    # assert_that(result).has_schema_id(credential_definition.schema_id)
    assert_that(result["id"]).is_not_empty()


@pytest.mark.asyncio
async def test_create_credential_definition_issuer_tenant(
    schema_definition: CredentialSchema,
    faber_acapy_client: AcaPyClient,
    faber_client: AsyncClient,
):
    # This can go away once the schema integration with trust registry is merged
    await register_issuer(faber_client, schema_definition.id)

    credential_definition = CreateCredentialDefinition(
        schema_id=schema_definition.id, tag=get_random_string(5)
    )

    auth = acapy_auth_verified(acapy_auth(faber_client.headers["x-api-key"]))

    # when
    result = (
        await definitions.create_credential_definition(
            credential_definition, faber_acapy_client, auth
        )
    ).dict()

    faber_public_did = await get_public_did(faber_acapy_client)
    schema = await faber_acapy_client.schema.get_schema(schema_id=schema_definition.id)

    assert_that(result).has_id(
        f"{faber_public_did.did}:3:CL:{schema.schema_.seq_no}:{credential_definition.tag}"
    )
    assert_that(result).has_tag(credential_definition.tag)
