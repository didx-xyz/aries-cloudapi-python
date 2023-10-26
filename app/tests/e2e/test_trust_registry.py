import pytest
from assertpy import assert_that
from fastapi import HTTPException
from aries_cloudcontroller import AcaPyClient

from app.models.definitions import CredentialSchema
from app.models.tenants import CreateTenantResponse
from app.routes.trust_registry import router
from shared.constants import CLOUDAPI_URL
from shared.util.rich_async_client import RichAsyncClient

TRUST_REGISTRY = router.prefix


@pytest.mark.anyio
async def test_get_schemas(
    schema_definition: CredentialSchema,  # pylint: disable=unused-argument
    schema_definition_alt: CredentialSchema,  # pylint: disable=unused-argument
):
    async with RichAsyncClient() as client:
        schemas_response = await client.get(f"{CLOUDAPI_URL}{TRUST_REGISTRY}/schemas")

    assert schemas_response.status_code == 200
    schemas = schemas_response.json()
    assert len(schemas) >= 2


@pytest.mark.anyio
async def test_get_schema_by_id(schema_definition: CredentialSchema):
    async with RichAsyncClient() as client:
        schema_response = await client.get(
            f"{CLOUDAPI_URL}{TRUST_REGISTRY}/schemas/{schema_definition.id}"
        )

    assert schema_response.status_code == 200
    schema = schema_response.json()
    assert_that(schema).contains("did", "name", "version", "id")

    with pytest.raises(HTTPException) as exc:
        async with RichAsyncClient() as client:
            schema_response = await client.get(
                f"{CLOUDAPI_URL}{TRUST_REGISTRY}/schemas/bad_schema_id"
            )

    assert exc.value.status_code == 404


@pytest.mark.anyio
async def test_get_actors(
    faber_issuer: CreateTenantResponse, faber_acapy_client: AcaPyClient
):
    async with RichAsyncClient() as client:
        all_actors = await client.get(f"{CLOUDAPI_URL}{TRUST_REGISTRY}/actors")
        assert all_actors.status_code == 200
        actors = all_actors.json()
        assert_that(actors[0]).contains(
            "id", "name", "roles", "did", "didcomm_invitation"
        )

        actors_by_id = await client.get(
            f"{CLOUDAPI_URL}{TRUST_REGISTRY}/actors?actor_id={faber_issuer.wallet_id}"
        )
        assert actors_by_id.status_code == 200
        actor = actors_by_id.json()[0]

        actor_did = actor["did"]
        did_result = await faber_acapy_client.wallet.get_public_did()
        assert actor_did == f"did:sov:{did_result.result.did}"

        actor_name = actor["name"]
        assert actor_name == faber_issuer.tenant_name
        assert_that(actor).contains("id", "name", "roles", "did", "didcomm_invitation")

        actors_by_did = await client.get(
            f"{CLOUDAPI_URL}{TRUST_REGISTRY}/actors?actor_did={actor_did}"
        )
        assert actors_by_did.status_code == 200
        assert_that(actors_by_did.json()[0]).contains(
            "id", "name", "roles", "did", "didcomm_invitation"
        )

        actors_by_name = await client.get(
            f"{CLOUDAPI_URL}{TRUST_REGISTRY}/actors?actor_name={faber_issuer.tenant_name}"
        )
        assert actors_by_name.status_code == 200
        assert_that(actors_by_name.json()[0]).contains(
            "id", "name", "roles", "did", "didcomm_invitation"
        )


@pytest.mark.anyio
async def test_get_actors_x():
    async with RichAsyncClient() as client:
        with pytest.raises(HTTPException) as exc:
            await client.get(
                f"{CLOUDAPI_URL}{TRUST_REGISTRY}/actors?actor_name=Bad_actor_name"
            )
        assert exc.value.status_code == 404

        with pytest.raises(HTTPException) as exc:
            await client.get(
                f"{CLOUDAPI_URL}{TRUST_REGISTRY}/actors?actor_id=Bad_actor_id"
            )
        assert exc.value.status_code == 404

        with pytest.raises(HTTPException) as exc:
            await client.get(
                f"{CLOUDAPI_URL}{TRUST_REGISTRY}/actors?actor_did=Bad_actor_did"
            )
        assert exc.value.status_code == 404

        with pytest.raises(HTTPException) as exc:
            await client.get(
                f"{CLOUDAPI_URL}{TRUST_REGISTRY}/actors?actor_did=Bad&actor_id=Request"
            )
        assert exc.value.status_code == 400


@pytest.mark.anyio
async def test_get_issuers(
    faber_issuer: CreateTenantResponse,  # pylint: disable=unused-argument
):
    async with RichAsyncClient() as client:
        actors = await client.get(f"{CLOUDAPI_URL}{TRUST_REGISTRY}/actors/issuers")
        assert actors.status_code == 200


@pytest.mark.anyio
async def test_get_verifiers(
    acme_verifier: CreateTenantResponse,  # pylint: disable=unused-argument
):
    async with RichAsyncClient() as client:
        actors = await client.get(f"{CLOUDAPI_URL}{TRUST_REGISTRY}/actors/verifiers")
        assert actors.status_code == 200
