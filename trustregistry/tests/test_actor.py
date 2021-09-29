from fastapi.testclient import TestClient
import json

import dependencies
from registry import actors
import main

with open(dependencies.REGISTRY_FILE_PATH) as tr:
    actors_list = json.load(tr)["actors"]

existing_actor = actors_list[0]

non_existing_actor = {
    "id": "darth-vader",
    "name": "Darth Vader",
    "roles": ["issuer", "verifier"],
    "didcomm_invitation": "string",
    "did": "string",
}

client = TestClient(main.app)


def test_actor_exists():
    assert actors._actor_exists(existing_actor["id"], actors_list) is True
    assert actors._actor_exists("darth-vader", actors_list) is False


def test_get_schemas():
    response = client.get("/registry/actors")
    assert response.status_code == 200
    assert response.json() == actors_list


def test_register_actor():
    payload = json.dumps(non_existing_actor)
    response = client.post(
        "/registry/actors/",
        headers={"content-type": "application/json", "accept": "application/json"},
        data=payload,
    )
    assert response.json() == {}
    assert response.status_code == 200

    new_actor_resp = client.get("/registry/actors")
    assert new_actor_resp.status_code == 200
    new_actors = new_actor_resp.json()
    assert non_existing_actor["id"] in [actor["id"] for actor in new_actors]

    response = client.post(
        "/registry/actors/",
        headers={"content-type": "application/json", "accept": "application/json"},
        data=payload,
    )
    assert response.status_code == 405
    assert "Actor alrady exists" in response.json()["detail"]


def test_update_actor():
    payload = json.dumps(existing_actor)
    #     assert existing_actor == ""
    response = client.post(
        "/registry/actors/yoma-africa",
        headers={"content-type": "application/json", "accept": "application/json"},
        data=payload,
    )
    assert response.json() == {}
    assert response.status_code == 200

    new_actors_resp = client.get("/registry/actors")
    assert new_actors_resp.status_code == 200
    new_actors_list = new_actors_resp.json()
    assert existing_actor in new_actors_list

    response = client.post(
        "/registry/actors/idonotexist",
        headers={"content-type": "application/json", "accept": "application/json"},
        data=payload,
    )
    assert response.status_code == 404
    assert "Actor not found" in response.json()["detail"]


def test_remove_schema():
    response = client.delete("/registry/actors/darth-vader")
    assert response.json() == {}
    assert response.status_code == 200

    response = client.delete(
        "/registry/actors/darth-vader",
        headers={"content-type": "application/json", "accept": "application/json"},
    )
    assert response.status_code == 404
    assert "Actor not found" in response.json()["detail"]
