import json

from . import test_main

client = test_main.client

new_actor = {
    "id": "darth-vader",
    "name": "Darth Vader",
    "roles": ["issuer", "verifier"],
    "didcomm_invitation": "string",
    "did": "did:key:string",
}


def test_get_actors():
    response = client.get("/registry/actors")
    assert response.status_code == 200
    assert response.json() == {"actors": []}


def test_register_actor():
    payload = json.dumps(new_actor)
    response = client.post(
        "/registry/actors/",
        headers={"content-type": "application/json", "accept": "application/json"},
        data=payload,
    )
    assert response.json() == json.loads(payload)
    assert response.status_code == 200

    new_actor_resp = client.get("/registry/actors")
    assert new_actor_resp.status_code == 200
    new_actors = new_actor_resp.json()
    assert new_actor["id"] in [actor["id"] for actor in new_actors["actors"]]

    response = client.post(
        "/registry/actors/",
        headers={"content-type": "application/json", "accept": "application/json"},
        data=payload,
    )
    assert response.status_code == 405
    assert "Actor already exists" in response.json()["detail"]


def test_update_actor():
    payload = json.dumps(new_actor)
    response = client.post(
        "/registry/actors/darth-vader",
        headers={"content-type": "application/json", "accept": "application/json"},
        data=payload,
    )
    assert response.status_code == 200
    assert response.json() == new_actor

    new_actors_resp = client.get("/registry/actors")
    assert new_actors_resp.status_code == 200
    new_actors_list = new_actors_resp.json()
    assert new_actor in new_actors_list["actors"]

    response = client.post(
        "/registry/actors/idonotexist",
        headers={"content-type": "application/json", "accept": "application/json"},
        data=payload,
    )
    assert response.status_code == 404
    assert "Actor not found" in response.json()["detail"]


def test_remove_schema():
    response = client.delete("/registry/actors/darth-vader")
    assert response.status_code == 200
    assert response.json() is None

    response = client.delete(
        "/registry/actors/darth-vader",
        headers={"content-type": "application/json", "accept": "application/json"},
    )
    assert response.status_code == 404
    assert "Actor not found" in response.json()["detail"]
