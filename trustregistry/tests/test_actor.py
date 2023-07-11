import json

import pytest
from httpx import AsyncClient

from shared import TRUST_REGISTRY_URL

new_actor = {
    "id": "darth-vader",
    "name": "Darth Vader",
    "roles": ["issuer", "verifier"],
    "didcomm_invitation": "string",
    "did": "did:key:string",
}
dup_name_actor = {
    "id": "darth-vader2",
    "name": "Darth Vader",
    "roles": ["issuer", "verifier"],
    "didcomm_invitation": "string2",
    "did": "did:key:string2",
}
dup_did_actor = {
    "id": "darth-vader3",
    "name": "Darth Vader3",
    "roles": ["issuer", "verifier"],
    "didcomm_invitation": "string3",
    "did": "did:key:string",
}
dup_didcomm_actor = {
    "id": "darth-vader4",
    "name": "Darth Vader4",
    "roles": ["issuer", "verifier"],
    "didcomm_invitation": "string",
    "did": "did:key:string4",
}
dup_id_actor = {
    "id": "darth-vader",
    "name": "Darth Vader5",
    "roles": ["issuer", "verifier"],
    "didcomm_invitation": "string5",
    "did": "did:key:string5",
}
actor_id = new_actor["id"]


@pytest.mark.anyio
async def test_get_actors():
    async with AsyncClient() as client:
        response = await client.get(f"{TRUST_REGISTRY_URL}/registry/actors")

    assert response.status_code == 200
    assert "actors" in response.json()


@pytest.mark.anyio
async def test_register_actor():
    payload = json.dumps(new_actor)
    name_payload = json.dumps(dup_name_actor)
    did_payload = json.dumps(dup_did_actor)
    didcomm_payload = json.dumps(dup_didcomm_actor)
    id_payload = json.dumps(dup_id_actor)
    async with AsyncClient() as client:
        response = await client.post(
            f"{TRUST_REGISTRY_URL}/registry/actors",
            content=payload,
        )
        assert response.json() == json.loads(payload)
        assert response.status_code == 200

        new_actor_resp = await client.get(f"{TRUST_REGISTRY_URL}/registry/actors")
        assert new_actor_resp.status_code == 200
        new_actors = new_actor_resp.json()
        assert new_actor["id"] in [actor["id"] for actor in new_actors["actors"]]

        response = await client.post(
            f"{TRUST_REGISTRY_URL}/registry/actors",
            content=name_payload,
        )
        assert response.status_code == 409
        assert "Bad request: The requested actor name:" in response.json()["detail"]

        )
        assert response.status_code == 405
        assert "Actor already exists" in response.json()["detail"]


@pytest.mark.anyio
async def test_update_actor():
    async with AsyncClient() as client:
        response = await client.put(
            f"{TRUST_REGISTRY_URL}/registry/actors/{actor_id}",
            json=new_actor,
        )
        assert response.status_code == 200
        assert response.json() == new_actor

        new_actors_resp = await client.get(f"{TRUST_REGISTRY_URL}/registry/actors")
        assert new_actors_resp.status_code == 200
        new_actors_list = new_actors_resp.json()
        assert new_actor in new_actors_list["actors"]

        response = await client.put(
            f"{TRUST_REGISTRY_URL}/registry/actors/idonotexist",
            json=new_actor,
        )
        assert response.status_code == 400


@pytest.mark.anyio
async def test_update_actor_x():
    updated_actor = new_actor.copy()
    updated_actor["did"] = None

    async with AsyncClient() as client:
        response = await client.put(
            f"{TRUST_REGISTRY_URL}/registry/actors/{actor_id}",
            json=updated_actor,
        )

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "loc": ["body", "did"],
                "msg": "none is not an allowed value",
                "type": "type_error.none.not_allowed",
            }
        ]
    }


@pytest.mark.anyio
async def test_remove_actors():
    async with AsyncClient() as client:
        response = await client.delete(
            f"{TRUST_REGISTRY_URL}/registry/actors/{actor_id}"
        )
        assert response.status_code == 204
        assert not response.text

        response = await client.delete(
            f"{TRUST_REGISTRY_URL}/registry/actors/{actor_id}"
        )
        assert response.status_code == 404
        assert "Actor not found" in response.json()["detail"]
