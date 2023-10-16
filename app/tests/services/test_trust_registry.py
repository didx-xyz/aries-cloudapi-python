from unittest.mock import AsyncMock, Mock
from fastapi import HTTPException

import pytest
from httpx import HTTPStatusError, Response
from pytest_mock import MockerFixture

from app.exceptions.trust_registry_exception import TrustRegistryException
from app.models.trust_registry import Actor
from app.services.trust_registry.actors import (
    actor_by_did,
    actors_with_role,
    register_actor,
    remove_actor_by_id,
    update_actor,
)
from app.services.trust_registry.schemas import register_schema, remove_schema_by_id
from app.services.trust_registry.util.actor import actor_has_role, assert_actor_name
from app.services.trust_registry.util.issuer import assert_valid_issuer
from app.services.trust_registry.util.schema import registry_has_schema
from app.routes.trust_registry import (
    get_schemas,
    get_schema_by_id,
    get_actors,
    get_issuers,
    get_verifiers,
)
from shared.constants import TRUST_REGISTRY_URL


@pytest.fixture
def mock_async_client(mocker: MockerFixture) -> Mock:
    patch_async_client = mocker.patch("app.services.trust_registry.RichAsyncClient")

    mocked_async_client = Mock()
    response = Response(status_code=200)
    mocked_async_client.get = AsyncMock(return_value=response)
    patch_async_client.return_value.__aenter__.return_value = mocked_async_client

    return mocked_async_client


@pytest.mark.anyio
async def test_assert_valid_issuer(mock_async_client):
    did = "did:sov:xxxx"
    actor = {"id": "actor-id", "roles": ["issuer"], "did": did}
    schema_id = "a_schema_id"

    # Mock the actor_by_did and registry_has_schema calls
    response = Response(
        status_code=200,
        json={"id": schema_id, "did": did, "version": "1.0", "name": "name"},
    )
    response.raise_for_status = Mock()
    mock_async_client.get = AsyncMock(
        side_effect=[
            Response(200, json=actor),
            response,
        ]
    )

    await assert_valid_issuer(did=did, schema_id=schema_id)

    # No actor with specified did
    mock_async_client.get = AsyncMock(return_value=Response(404))
    with pytest.raises(TrustRegistryException):
        await assert_valid_issuer(did=did, schema_id=schema_id)

    # Actor does not have required role 'issuer'
    mock_async_client.get = AsyncMock(
        return_value=Response(
            200, json={"id": "actor-id", "roles": ["verifier"], "did": did}
        )
    )
    with pytest.raises(TrustRegistryException):
        await assert_valid_issuer(did=did, schema_id=schema_id)

    # Schema is not registered in registry
    not_found_response = Response(status_code=404)
    not_found_response.raise_for_status = Mock(
        side_effect=HTTPStatusError(
            response=not_found_response,
            message="Schema not found in registry",
            request=schema_id,
        )
    )
    mock_async_client.get = AsyncMock(
        side_effect=[
            Response(200, json=actor),
            not_found_response,
        ]
    )
    with pytest.raises(TrustRegistryException):
        await assert_valid_issuer(did=did, schema_id=schema_id)


@pytest.mark.anyio
async def test_actor_has_role(mock_async_client):
    mock_async_client.get = AsyncMock(
        return_value=Response(200, json={"roles": ["verifier"]})
    )
    assert await actor_has_role("governance", "issuer") is False

    mock_async_client.get = AsyncMock(
        return_value=Response(428, json={"roles": ["verifier"]})
    )
    with pytest.raises(TrustRegistryException):
        await actor_has_role("governance", "issuer")

    mock_async_client.get = AsyncMock(
        return_value=Response(428, json={"roles": ["issuer"]})
    )
    with pytest.raises(TrustRegistryException):
        await actor_has_role("governance", "issuer")

    mock_async_client.get = AsyncMock(
        return_value=Response(200, json={"roles": ["issuer"]})
    )
    assert await actor_has_role("governance", "issuer") is True


@pytest.mark.anyio
async def test_actor_by_did(mock_async_client):
    res = {
        "id": "governance",
        "roles": ["verifier"],
    }

    mock_async_client.get = AsyncMock(return_value=Response(200, json=res))
    actor = await actor_by_did("did:sov:xxx")
    mock_async_client.get.assert_called_once_with(
        TRUST_REGISTRY_URL + "/registry/actors/did/did:sov:xxx"
    )
    assert actor == res

    mock_async_client.get = AsyncMock(return_value=Response(500, json=res))
    with pytest.raises(TrustRegistryException):
        actor = await actor_by_did("did:sov:xxx")

    mock_async_client.get = AsyncMock(return_value=Response(404, json={}))
    actor = await actor_by_did("did:sov:xxx")
    assert actor is None


@pytest.mark.anyio
async def test_actor_with_role(mock_async_client):
    actors = [
        {"id": "governance", "roles": ["issuer"]},
        {"id": "governance2", "roles": ["issuer"]},
    ]
    mock_async_client.get = AsyncMock(
        return_value=Response(200, json={"actors": actors})
    )
    assert await actors_with_role("issuer") == actors

    actors = [
        {"id": "governance", "roles": ["issuer"]},
        {"id": "governance2", "roles": ["verifier"]},
    ]
    mock_async_client.get = AsyncMock(
        return_value=Response(200, json={"actors": actors})
    )
    assert await actors_with_role("issuer") == [actors[0]]

    actors = [
        {"id": "governance", "roles": ["verifier"]},
        {"id": "governance2", "roles": ["verifier"]},
    ]
    mock_async_client.get = AsyncMock(
        return_value=Response(428, json={"actors": actors})
    )
    with pytest.raises(TrustRegistryException):
        await actors_with_role("issuer")

    actors = [
        {"id": "governance", "roles": ["verifier"]},
        {"id": "governance2", "roles": ["verifier"]},
    ]
    mock_async_client.get = AsyncMock(
        return_value=Response(200, json={"actors": actors})
    )
    assert await actors_with_role("issuer") == []


@pytest.mark.anyio
async def test_registry_has_schema(mock_async_client):
    schema_id = "did:name:version"
    did = "did:sov:xxxx"
    # mock has schema
    response = Response(
        status_code=200,
        json={"id": schema_id, "did": did, "version": "1.0", "name": "name"},
    )
    response.raise_for_status = Mock()
    mock_async_client.get = AsyncMock(return_value=response)
    assert await registry_has_schema(schema_id) is True

    schema_id = "did_3:name:version"
    # mock does not have schema
    not_found_response = Response(status_code=404)
    not_found_response.raise_for_status = Mock(
        side_effect=HTTPStatusError(
            response=not_found_response,
            message="Something went wrong when fetching schema from trust registry.",
            request=schema_id,
        )
    )

    mock_async_client.get = AsyncMock(return_value=not_found_response)
    assert await registry_has_schema(schema_id) is False

    # mock 500
    error_response = Response(status_code=500)
    error_response.raise_for_status = Mock(
        side_effect=HTTPStatusError(
            response=error_response,
            message="Something went wrong when fetching schema from trust registry.",
            request=schema_id,
        )
    )

    mock_async_client.get = AsyncMock(return_value=error_response)
    with pytest.raises(HTTPStatusError):
        await registry_has_schema(schema_id)


@pytest.mark.anyio
async def test_register_schema(mock_async_client):
    schema_id = "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0"
    mock_async_client.post = AsyncMock(return_value=Response(200))
    await register_schema(schema_id=schema_id)
    mock_async_client.post.assert_called_once_with(
        TRUST_REGISTRY_URL + "/registry/schemas",
        json={"schema_id": schema_id},
    )

    mock_async_client.post = AsyncMock(return_value=Response(500))
    with pytest.raises(TrustRegistryException):
        await register_schema(schema_id=schema_id)


@pytest.mark.anyio
async def test_register_actor(mock_async_client):
    actor = Actor(
        id="actor-id",
        name="actor-name",
        roles=["issuer", "verifier"],
        did="actor-did",
        didcomm_invitation="actor-didcomm-invitation",
    )
    mock_async_client.post = AsyncMock(return_value=Response(200))
    await register_actor(actor=actor)
    mock_async_client.post.assert_called_once_with(
        TRUST_REGISTRY_URL + "/registry/actors", json=actor
    )

    mock_async_client.post = AsyncMock(return_value=Response(500))
    with pytest.raises(TrustRegistryException):
        await register_actor(actor=actor)

    mock_async_client.post = AsyncMock(
        return_value=Response(422, json={"error": "some error"})
    )
    with pytest.raises(TrustRegistryException):
        await register_actor(actor=actor)


@pytest.mark.anyio
async def test_remove_actor_by_id(mock_async_client):
    actor_id = "actor_id"
    mock_async_client.delete = AsyncMock(return_value=Response(200))
    await remove_actor_by_id(actor_id=actor_id)
    mock_async_client.delete.assert_called_once_with(
        TRUST_REGISTRY_URL + f"/registry/actors/{actor_id}"
    )

    mock_async_client.delete = AsyncMock(return_value=Response(500))
    with pytest.raises(TrustRegistryException):
        await remove_actor_by_id(actor_id="actor_id")


@pytest.mark.anyio
async def test_remove_schema_by_id(mock_async_client):
    schema_id = "schema_id"
    mock_async_client.delete = AsyncMock(return_value=Response(200))
    await remove_schema_by_id(schema_id=schema_id)
    mock_async_client.delete.assert_called_once_with(
        TRUST_REGISTRY_URL + f"/registry/schemas/{schema_id}"
    )

    mock_async_client.delete = AsyncMock(return_value=Response(500, text="The error"))
    with pytest.raises(
        TrustRegistryException, match="Error removing schema from trust registry"
    ):
        await remove_schema_by_id(schema_id="schema_id")


@pytest.mark.anyio
async def test_update_actor(mock_async_client):
    actor_id = "actor_id"
    actor = Actor(
        id=actor_id,
        name="actor-name",
        roles=["issuer", "verifier"],
        did="actor-did",
        didcomm_invitation="actor-didcomm-invitation",
    )

    mock_async_client.put = AsyncMock(return_value=Response(200, json=actor))
    await update_actor(actor=actor)
    mock_async_client.put.assert_called_once_with(
        TRUST_REGISTRY_URL + f"/registry/actors/{actor_id}", json=actor
    )

    mock_async_client.put = AsyncMock(return_value=Response(500))
    with pytest.raises(TrustRegistryException):
        await update_actor(actor=actor)

    mock_async_client.put = AsyncMock(
        return_value=Response(422, json={"error": "some error"})
    )
    with pytest.raises(TrustRegistryException):
        await update_actor(actor=actor)


@pytest.mark.anyio
async def test_assert_actor_name(mock_async_client):
    # test actor exists
    name = "Numuhukumakiaki'aialunamor"
    actor = Actor(
        id="some_id",
        name=name,
        roles=["issuer", "verifier"],
        did="actor-did",
        didcomm_invitation="actor-didcomm-invitation",
    )
    mock_async_client.get = AsyncMock(
        return_value=Response(status_code=200, json=actor)
    )

    assert await assert_actor_name(name) is True

    # test actor does not exists
    mock_async_client.get = AsyncMock(return_value=Response(status_code=404))

    assert await assert_actor_name("not_an_actor") is False

    # test exception (500)
    mock_async_client.get = AsyncMock(return_value=Response(500))
    with pytest.raises(TrustRegistryException):
        await assert_actor_name(name)
