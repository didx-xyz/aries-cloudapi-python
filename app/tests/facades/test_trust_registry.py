from unittest.mock import patch

import pytest

import app.facades.trust_registry as trf


@pytest.mark.anyio
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
            trf.TrustRegistryException,
            match=f"Did {did} not registered in the trust registry",
        ):
            await trf.assert_valid_issuer(did=did, schema_id=schema_id)

    # Actor does not have required role 'issuer'
    with patch.object(trf, "actor_by_did") as mock_actor_by_did:
        mock_actor_by_did.return_value = {**actor, "roles": ["verifier"]}

        with pytest.raises(
            trf.TrustRegistryException,
            match="Actor actor-id does not have required role 'issuer'",
        ):
            await trf.assert_valid_issuer(did=did, schema_id=schema_id)

    # Schema is not registered in registry
    with patch.object(trf, "actor_by_did") as mock_actor_by_did, patch.object(
        trf, "registry_has_schema"
    ) as mock_registry_has_schema:
        mock_actor_by_did.return_value = actor
        mock_registry_has_schema.return_value = False

        with pytest.raises(
            trf.TrustRegistryException,
            match=f"Schema with id {schema_id} is not registered in trust registry",
        ):
            await trf.assert_valid_issuer(did=did, schema_id=schema_id)


@pytest.mark.anyio
async def test_actor_has_role():
    with patch("httpx.get") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.is_error = False
        mock_request.return_value.json.return_value = {"roles": ["verifier"]}

        assert await trf.actor_has_role("governance", "issuer") is False

    with patch("httpx.get") as mock_request:
        mock_request.return_value.status_code = 428
        mock_request.return_value.json.return_value = {"roles": ["verifier"]}

        with pytest.raises(trf.TrustRegistryException):
            await trf.actor_has_role("governance", "issuer")

    with patch("httpx.get") as mock_request:
        mock_request.return_value.status_code = 428
        mock_request.return_value.json.return_value = {"roles": ["issuer"]}

        with pytest.raises(trf.TrustRegistryException):
            await trf.actor_has_role("governance", "issuer")

    with patch("httpx.get") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.is_error = False
        mock_request.return_value.json.return_value = {"roles": ["issuer"]}

        assert await trf.actor_has_role("governance", "issuer") is True


@pytest.mark.anyio
async def test_actor_by_did():
    with patch("httpx.get") as mock_request:
        res = {
            "id": "governance",
            "roles": ["verifier"],
        }

        mock_request.return_value.status_code = 200
        mock_request.return_value.is_error = False
        mock_request.return_value.json.return_value = res

        actor = await trf.actor_by_did("did:sov:xxx")
        mock_request.assert_called_once_with(
            trf.TRUST_REGISTRY_URL + "/registry/actors/did/did:sov:xxx"
        )
        assert actor is res

    with patch("httpx.get") as mock_request:
        res = {
            "id": "governance",
            "roles": ["verifier"],
        }

        mock_request.return_value.status_code = 500
        mock_request.return_value.is_error = True
        mock_request.return_value.json.return_value = res

        with pytest.raises(trf.TrustRegistryException):
            actor = await trf.actor_by_did("did:sov:xxx")

        mock_request.assert_called_once_with(
            trf.TRUST_REGISTRY_URL + "/registry/actors/did/did:sov:xxx"
        )

    with patch("httpx.get") as mock_request:
        mock_request.return_value.status_code = 404
        mock_request.return_value.json.return_value = {}

        actor = await trf.actor_by_did("did:sov:xxx")
        mock_request.assert_called_once_with(
            trf.TRUST_REGISTRY_URL + "/registry/actors/did/did:sov:xxx"
        )
        assert actor is None


@pytest.mark.anyio
async def test_actor_with_role():
    with patch("httpx.get") as mock_request:
        actors = [
            {"id": "governance", "roles": ["issuer"]},
            {"id": "governance2", "roles": ["issuer"]},
        ]
        mock_request.return_value.status_code = 200
        mock_request.return_value.is_error = False
        mock_request.return_value.json.return_value = {"actors": actors}

        assert await trf.actors_with_role("issuer") == actors

    with patch("httpx.get") as mock_request:
        actors = [
            {"id": "governance", "roles": ["issuer"]},
            {"id": "governance2", "roles": ["verifier"]},
        ]
        mock_request.return_value.status_code = 200
        mock_request.return_value.is_error = False
        mock_request.return_value.json.return_value = {"actors": actors}

        assert await trf.actors_with_role("issuer") == [actors[0]]

    with patch("httpx.get") as mock_request, pytest.raises(trf.TrustRegistryException):
        actors = [
            {"id": "governance", "roles": ["verifier"]},
            {"id": "governance2", "roles": ["verifier"]},
        ]
        mock_request.return_value.status_code = 428
        mock_request.return_value.is_error = True
        mock_request.return_value.json.return_value = {"actors": actors}

        assert await trf.actors_with_role("issuer") == []

    with patch("httpx.get") as mock_request:
        actors = [
            {"id": "governance", "roles": ["verifier"]},
            {"id": "governance2", "roles": ["verifier"]},
        ]
        mock_request.return_value.status_code = 200
        mock_request.return_value.is_error = False
        mock_request.return_value.json.return_value = {"actors": actors}

        assert await trf.actors_with_role("issuer") == []


@pytest.mark.anyio
async def test_registry_has_schema():
    with patch("httpx.get") as mock_request:
        schemas = ["did:name:version", "did_2:name_2:version_2"]
        schema_id = "did:name:version"
        mock_request.return_value.status_code = 200
        mock_request.return_value.is_error = False
        mock_request.return_value.json.return_value = {"schemas": schemas}

        assert await trf.registry_has_schema(schema_id) is True

    with patch("httpx.get") as mock_request:
        schemas = ["did:name:version", "did_2:name_2:version_2"]
        schema_id = "did_3:name:version"
        mock_request.return_value.status_code = 200
        mock_request.return_value.is_error = False
        mock_request.return_value.json.return_value = {"schemas": schemas}

        assert await trf.registry_has_schema(schema_id) is False

    with patch("httpx.get") as mock_request:
        schemas = ["did:name:version", "did_2:name_2:version_2"]
        schema_id = "did_3:name:version"
        mock_request.return_value.is_error = True
        mock_request.return_value.status_code = 404

        assert await trf.registry_has_schema(schema_id) is False

    with patch("httpx.get") as mock_request, pytest.raises(trf.TrustRegistryException):
        schemas = ["did:name:version", "did_2:name_2:version_2"]
        schema_id = "did_3:name:version"
        mock_request.return_value.is_error = True
        mock_request.return_value.status_code = 500

        await trf.registry_has_schema(schema_id)


@pytest.mark.anyio
async def test_register_schema():
    with patch("httpx.post") as mock_request:
        schema_id = "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0"
        mock_request.return_value.status_code = 200
        mock_request.return_value.is_error = False

        await trf.register_schema(schema_id=schema_id)

        mock_request.assert_called_once_with(
            trf.TRUST_REGISTRY_URL + "/registry/schemas",
            json={"schema_id": schema_id},
        )

    with patch("httpx.post") as mock_request, pytest.raises(
        trf.TrustRegistryException,
        match="Error registering schema WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0: ",
    ):
        schema_id = "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0"
        mock_request.return_value.status_code = 500
        mock_request.return_value.is_error = True

        await trf.register_schema(schema_id=schema_id)


@pytest.mark.anyio
async def test_register_actor():
    actor = trf.Actor(
        id="actor-id",
        name="actor-name",
        roles=["issuer", "verifier"],
        did="actor-did",
        didcomm_invitation="actor-didcomm-invitation",
    )
    with patch("httpx.post") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.is_error = False

        await trf.register_actor(actor=actor)

        mock_request.assert_called_once_with(
            trf.TRUST_REGISTRY_URL + "/registry/actors", json=actor
        )

    with patch("httpx.post") as mock_request, pytest.raises(
        trf.TrustRegistryException, match="Error registering actor: "
    ):
        mock_request.return_value.status_code = 500
        mock_request.return_value.is_error = True

        await trf.register_actor(actor=actor)

    with patch("httpx.post") as mock_request, pytest.raises(trf.TrustRegistryException):
        mock_request.return_value.status_code = 422

        await trf.register_actor(actor=actor)


@pytest.mark.anyio
async def test_remove_actor_by_id():
    with patch("httpx.delete") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.is_error = False

        actor_id = "actor_id"
        await trf.remove_actor_by_id(actor_id=actor_id)

        mock_request.assert_called_once_with(
            trf.TRUST_REGISTRY_URL + f"/registry/actors/{actor_id}"
        )

    with patch("httpx.delete") as mock_request, pytest.raises(
        trf.TrustRegistryException,
        match="Error removing actor from trust registry: The error",
    ):
        mock_request.return_value.status_code = 500
        mock_request.return_value.is_error = True
        mock_request.return_value.text = "The error"

        await trf.remove_actor_by_id(actor_id="actor_id")


@pytest.mark.anyio
async def test_remove_schema_by_id():
    with patch("httpx.delete") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.is_error = False

        schema_id = "schema_id"
        await trf.remove_schema_by_id(schema_id=schema_id)

        mock_request.assert_called_once_with(
            trf.TRUST_REGISTRY_URL + f"/registry/schemas/{schema_id}"
        )

    with patch("httpx.delete") as mock_request, pytest.raises(
        trf.TrustRegistryException,
        match="Error removing schema from trust registry: The error",
    ):
        mock_request.return_value.status_code = 500
        mock_request.return_value.is_error = True
        mock_request.return_value.text = "The error"

        await trf.remove_schema_by_id(schema_id="schema_id")


@pytest.mark.anyio
async def test_get_actor_by_did():
    with patch("httpx.get") as mock_request:
        res = {
            "actors": [],
            "schemas": [],
        }

        mock_request.return_value.status_code = 200
        mock_request.return_value.is_error = False
        mock_request.return_value.json.return_value = res

        tr = await trf.get_trust_registry()
        mock_request.assert_called_once_with(trf.TRUST_REGISTRY_URL + "/registry")
        assert tr is res

    with patch("httpx.get") as mock_request, pytest.raises(trf.TrustRegistryException):
        res = {
            "actors": [],
            "schemas": [],
        }

        mock_request.return_value.status_code = 500
        mock_request.return_value.is_error = True
        mock_request.return_value.json.return_value = res

        tr = await trf.get_trust_registry()

    with patch("httpx.get") as mock_request, pytest.raises(trf.TrustRegistryException):
        mock_request.return_value.status_code = 404
        mock_request.return_value.is_error = True
        mock_request.return_value.json.return_value = {}

        tr = await trf.get_trust_registry()


@pytest.mark.anyio
async def test_update_actor():
    actor_id = "actor_id"
    actor = trf.Actor(
        id=actor_id,
        name="actor-name",
        roles=["issuer", "verifier"],
        did="actor-did",
        didcomm_invitation="actor-didcomm-invitation",
    )

    with patch("httpx.post") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.is_error = False

        await trf.update_actor(actor=actor)

        mock_request.assert_called_once_with(
            trf.TRUST_REGISTRY_URL + f"/registry/actors/{actor_id}", json=actor
        )

    with patch("httpx.post") as mock_request, pytest.raises(
        trf.TrustRegistryException,
        match="Error updating actor in trust registry: The error",
    ):
        mock_request.return_value.status_code = 500
        mock_request.return_value.is_error = True
        mock_request.return_value.text = "The error"

        await trf.update_actor(actor=actor)

    with patch("httpx.post") as mock_request, pytest.raises(trf.TrustRegistryException):
        mock_request.return_value.status_code = 422

        await trf.update_actor(actor=actor)
