from unittest.mock import patch

import pytest
from fastapi.exceptions import HTTPException

import app.trust_registry_facade as trf


@pytest.mark.asyncio
async def test_assert_valid_issuer():
    did = "did:sov:xxxx"
    actor = {"id": "actor-id", "roles": ["issuer"], "did": did}
    schema_id = "a_schema_id"

    # Success
    with patch.object(trf, "actor_by_did") as mock_actor_by_did, patch.object(
        trf, "registry_has_schema"
    ) as mock_registry_has_schema:
        mock_actor_by_did.return_value = actor
        mock_registry_has_schema.return_value = True

        await trf.assert_valid_issuer(did=did, schema_id=schema_id)

        mock_actor_by_did.assert_called_once_with(did)
        mock_registry_has_schema.assert_called_once_with(schema_id)

    # No actor with specified did
    with patch.object(trf, "actor_by_did") as mock_actor_by_did, patch.object(
        trf, "registry_has_schema"
    ) as mock_registry_has_schema:
        mock_actor_by_did.return_value = None

        with pytest.raises(
            Exception, match=f"Did {did} not registered in the trust registry"
        ):
            await trf.assert_valid_issuer(did=did, schema_id=schema_id)

    # Actor does not have required role 'issuer'
    with patch.object(trf, "actor_by_did") as mock_actor_by_did:
        mock_actor_by_did.return_value = {**actor, "roles": ["verifier"]}

        with pytest.raises(
            Exception, match="Actor actor-id does not have required role 'issuer'"
        ):
            await trf.assert_valid_issuer(did=did, schema_id=schema_id)

    # Schema is not registered in registry
    with patch.object(trf, "actor_by_did") as mock_actor_by_did, patch.object(
        trf, "registry_has_schema"
    ) as mock_registry_has_schema:
        mock_actor_by_did.return_value = actor
        mock_registry_has_schema.return_value = False

        with pytest.raises(
            Exception,
            match=f"Schema with id {schema_id} is not registered in trust registry",
        ):
            await trf.assert_valid_issuer(did=did, schema_id=schema_id)


@pytest.mark.asyncio
async def test_assert_valid_verifier():
    did = "did:sov:xxxx"
    actor = {"id": "actor-id", "roles": ["verifier"], "did": did}
    schema_id = "a_schema_id"

    # Success
    with patch.object(trf, "actor_by_did") as mock_actor_by_did, patch.object(
        trf, "registry_has_schema"
    ) as mock_registry_has_schema:
        mock_actor_by_did.return_value = actor
        mock_registry_has_schema.return_value = True

        await trf.assert_valid_verifier(did=did, schema_id=schema_id)

        mock_actor_by_did.assert_called_once_with(did)
        mock_registry_has_schema.assert_called_once_with(schema_id)

    # No actor with specified did
    with patch.object(trf, "actor_by_did") as mock_actor_by_did, patch.object(
        trf, "registry_has_schema"
    ) as mock_registry_has_schema:
        mock_actor_by_did.return_value = None

        with pytest.raises(
            Exception, match=f"Did {did} not registered in the trust registry"
        ):
            await trf.assert_valid_verifier(did=did, schema_id=schema_id)

    # Actor does not have required role 'issuer'
    with patch.object(trf, "actor_by_did") as mock_actor_by_did:
        mock_actor_by_did.return_value = {**actor, "roles": ["issuer"]}

        with pytest.raises(
            Exception, match="Actor actor-id does not have required role 'verifier'"
        ):
            await trf.assert_valid_verifier(did=did, schema_id=schema_id)

    # Schema is not registered in registry
    with patch.object(trf, "actor_by_did") as mock_actor_by_did, patch.object(
        trf, "registry_has_schema"
    ) as mock_registry_has_schema:
        mock_actor_by_did.return_value = actor
        mock_registry_has_schema.return_value = False

        with pytest.raises(
            Exception,
            match=f"Schema with id {schema_id} is not registered in trust registry",
        ):
            await trf.assert_valid_verifier(did=did, schema_id=schema_id)


@pytest.mark.asyncio
async def test_actor_has_schema():
    with patch("requests.get") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.text = "{}"

        assert await trf.actor_has_schema("1", "2") is False

    with patch("requests.get") as mock_request:
        mock_request.return_value.status_code = 428
        mock_request.return_value.text = "{}"

        assert await trf.actor_has_schema("1", "2") is False

    with patch("requests.get") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = {"schemas": ["schema_id"]}

        assert await trf.actor_has_schema("1", "schema_id") is True


@pytest.mark.asyncio
async def test_actor_has_role():
    with patch("requests.get") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = {"roles": ["verifier"]}

        assert await trf.actor_has_role("yoma", "issuer") is False

    with patch("requests.get") as mock_request:
        mock_request.return_value.status_code = 428
        mock_request.return_value.json.return_value = {"roles": ["verifier"]}

        with pytest.raises(HTTPException):
            await trf.actor_has_role("yoma", "issuer")

    with patch("requests.get") as mock_request:
        mock_request.return_value.status_code = 428
        mock_request.return_value.json.return_value = {"roles": ["issuer"]}

        with pytest.raises(HTTPException):
            await trf.actor_has_role("yoma", "issuer")

    with patch("requests.get") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = {"roles": ["issuer"]}

        assert await trf.actor_has_role("yoma", "issuer") is True


@pytest.mark.asyncio
async def test_actor_by_did():
    with patch("requests.get") as mock_request:
        res = {
            "id": "yoma",
            "roles": ["verifier"],
        }

        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = res

        actor = await trf.actor_by_did("did:sov:xxx")
        mock_request.assert_called_once_with(
            trf.TRUST_REGISTRY_URL + "registry/actors/did/did:sov:xxx"
        )
        assert actor is res

    with patch("requests.get") as mock_request:
        mock_request.return_value.status_code = 404
        mock_request.return_value.json.return_value = {}

        actor = await trf.actor_by_did("did:sov:xxx")
        mock_request.assert_called_once_with(
            trf.TRUST_REGISTRY_URL + "registry/actors/did/did:sov:xxx"
        )
        assert actor is None


@pytest.mark.asyncio
async def test_actor_with_role():
    with patch("requests.get") as mock_request:
        actors = [
            {"id": "yoma", "roles": ["issuer"]},
            {"id": "yoma2", "roles": ["issuer"]},
        ]
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = {"actors": actors}

        assert await trf.actors_with_role("issuer") == actors

    with patch("requests.get") as mock_request:
        actors = [
            {"id": "yoma", "roles": ["issuer"]},
            {"id": "yoma2", "roles": ["verifier"]},
        ]
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = {"actors": actors}

        assert await trf.actors_with_role("issuer") == [actors[0]]

    with patch("requests.get") as mock_request:
        actors = [
            {"id": "yoma", "roles": ["issuer"]},
            {"id": "yoma2", "roles": ["verifier"]},
        ]
        mock_request.return_value.status_code = 428
        mock_request.return_value.json.return_value = {"actors": actors}

        assert await trf.actors_with_role("issuer") == []

    with patch("requests.get") as mock_request:
        actors = [
            {"id": "yoma", "roles": ["verifier"]},
            {"id": "yoma2", "roles": ["verifier"]},
        ]
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = {"actors": actors}

        assert await trf.actors_with_role("issuer") == []


@pytest.mark.asyncio
async def test_registry_has_schema():
    with patch("requests.get") as mock_request:
        schemas = ["did:name:version", "did_2:name_2:version_2"]
        schema_id = "did:name:version"
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = {"schemas": schemas}

        assert await trf.registry_has_schema(schema_id) is True

    with patch("requests.get") as mock_request:
        schemas = ["did:name:version", "did_2:name_2:version_2"]
        schema_id = "did_3:name:version"
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = {"schemas": schemas}

        assert await trf.registry_has_schema(schema_id) is False

    with patch("requests.get") as mock_request:
        schemas = ["did:name:version", "did_2:name_2:version_2"]
        schema_id = "did_3:name:version"
        mock_request.return_value.status_code = 418

        assert await trf.registry_has_schema(schema_id) is False


@pytest.mark.asyncio
async def test_get_did_for_actor():
    with patch("requests.get") as mock_request:
        actor = {
            "id": "yoma",
            "roles": ["verifier"],
            "did": "actor_did",
            "didcomm_invitation": "invite",
        }
        mock_request.return_value.status_code = 418

        assert await trf.get_did_for_actor("yoma") is None

    with patch("requests.get") as mock_request:
        actor = {
            "id": "yoma",
            "roles": ["verifier"],
            "did": "actor_did",
            "didcomm_invitation": "invite",
        }
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = actor

        assert await trf.get_did_for_actor("yoma") == ["actor_did", "invite"]

    with patch("requests.get") as mock_request:
        actor = {
            "id": "yoma",
            "roles": ["verifier"],
            "did": None,
            "didcomm_invitation": None,
        }
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = actor

        assert await trf.get_did_for_actor("yoma") == [None, None]


@pytest.mark.asyncio
async def test_register_schema():
    with patch("requests.post") as mock_request:
        schema_id = "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0"
        mock_request.return_value.status_code = 200

        await trf.register_schema(schema_id=schema_id)

        mock_request.assert_called_once_with(
            trf.TRUST_REGISTRY_URL + "/registry/schemas",
            json={
                "did": "WgWxqztrNooG92RXvxSTWv",
                "name": "schema_name",
                "version": "1.0",
            },
        )

    with patch("requests.post") as mock_request, pytest.raises(
        Exception, match="Error registering schema: "
    ):
        schema_id = "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0"
        mock_request.return_value.status_code = 500

        await trf.register_schema(schema_id=schema_id)


@pytest.mark.asyncio
async def test_register_actor():
    actor = trf.Actor(
        id="actor-id",
        name="actor-name",
        roles=["issuer", "verifier"],
        did="actor-did",
        didcomm_invitation="actor-didcomm-invitation",
    )
    with patch("requests.post") as mock_request:
        mock_request.return_value.status_code = 200

        await trf.register_actor(actor=actor)

        mock_request.assert_called_once_with(
            trf.TRUST_REGISTRY_URL + "/registry/actors", json=actor
        )

    with patch("requests.post") as mock_request, pytest.raises(
        Exception, match="Error registering actor: "
    ):
        mock_request.return_value.status_code = 500

        await trf.register_actor(actor=actor)
