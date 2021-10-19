from unittest.mock import patch

import pytest
from fastapi.exceptions import HTTPException

import app.trust_registry_facade as trf


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
        mock_request.return_value.json.return_value = {"schemas": "schema_id"}

        assert await trf.actor_has_schema("1", "schema_id") is True


@pytest.mark.asyncio
async def test_actor_has_role():
    with patch("requests.get") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = {"roles": "verifier"}

        assert await trf.actor_has_role("yoma", "issuer") is False

    with patch("requests.get") as mock_request:
        mock_request.return_value.status_code = 428
        mock_request.return_value.json.return_value = {"roles": "verifier"}

        with pytest.raises(HTTPException):
            await trf.actor_has_role("yoma", "issuer")

    with patch("requests.get") as mock_request:
        mock_request.return_value.status_code = 428
        mock_request.return_value.json.return_value = {"roles": "issuer"}

        with pytest.raises(HTTPException):
            await trf.actor_has_role("yoma", "issuer")

    with patch("requests.get") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = {"roles": "issuer"}

        assert await trf.actor_has_role("yoma", "issuer") is True


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
