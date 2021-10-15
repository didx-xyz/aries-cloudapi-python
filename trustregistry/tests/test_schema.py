import json

from trustregistry.tests.test_main import client


def test_get_schemas():
    response = client.get("/registry/schemas")
    assert response.status_code == 200
    assert response.json() == {"schemas": []}


def test_register_schema():
    payload = json.dumps({"did": "string", "name": "string", "version": "string"})
    response = client.post(
        "/registry/schemas/",
        headers={"content-type": "application/json", "accept": "application/json"},
        data=payload,
    )
    assert response.json() == json.loads(payload)
    assert response.status_code == 200

    new_schemas_resp = client.get("/registry/schemas")
    assert new_schemas_resp.status_code == 200
    new_schemas = new_schemas_resp.json()
    assert "string:string:string" in new_schemas["schemas"]

    response = client.post(
        "/registry/schemas/",
        headers={"content-type": "application/json", "accept": "application/json"},
        data=payload,
    )
    assert response.status_code == 405
    assert "Schema already exists" in response.json()["detail"]


def test_update_schema():
    payload = json.dumps({"did": "string", "name": "string", "version": "string"})
    response = client.post(
        "/registry/schemas/string",
        headers={"content-type": "application/json", "accept": "application/json"},
        data=payload,
    )
    assert response.json() == json.loads(payload)
    assert response.status_code == 200

    new_schemas_resp = client.get("/registry/schemas")
    assert new_schemas_resp.status_code == 200
    new_schemas = new_schemas_resp.json()
    assert "string:string:string" in new_schemas["schemas"]

    response = client.post(
        "/registry/schemas/idonotexist",
        headers={"content-type": "application/json", "accept": "application/json"},
        data=payload,
    )
    assert response.status_code == 405
    assert "Schema not found" in response.json()["detail"]


def test_remove_schema():
    response = client.delete("/registry/schemas/string")
    assert response.status_code == 200
    assert response.json() is None

    response = client.delete(
        "/registry/schemas/string",
        headers={"content-type": "application/json", "accept": "application/json"},
    )
    assert response.status_code == 404
    assert "Schema not found" in response.json()["detail"]
