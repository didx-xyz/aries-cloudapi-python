import json

from fastapi.testclient import TestClient
import dependencies
from registry import schemas
import main

with open(dependencies.REGISTRY_FILE_PATH) as tr:
    schemas_list = json.load(tr)["schemas"]

client = TestClient(main.app)


def test_get_schemas():
    response = client.get("/registry/schemas")
    assert response.status_code == 200
    assert response.json() == schemas_list


def test_schema_exists():
    schema_list = ["1234", "4321", "6789"]
    assert schemas._schema_exists("1234", schema_list)


def test_schema_exists_false():
    schema_list = ["1234", "4321", "6789"]
    assert not schemas._schema_exists("hello", schema_list)


def test_register_schema():
    payload = json.dumps({"did": "string", "name": "string", "version": "string"})
    response = client.post(
        "/registry/schemas/",
        headers={"content-type": "application/json", "accept": "application/json"},
        data=payload,
    )
    assert response.json() == {}
    assert response.status_code == 200

    new_schemas_resp = client.get("/registry/schemas")
    assert new_schemas_resp.status_code == 200
    new_schemas = new_schemas_resp.json()
    assert "string:string:string" in new_schemas

    response = client.post(
        "/registry/schemas/",
        headers={"content-type": "application/json", "accept": "application/json"},
        data=payload,
    )
    assert response.status_code == 405
    assert "Schema with ID string already exists" in response.json()["detail"]


def test_update_schema():
    payload = json.dumps({"did": "string", "name": "string", "version": "string"})
    response = client.post(
        "/registry/schemas/string",
        headers={"content-type": "application/json", "accept": "application/json"},
        data=payload,
    )
    assert response.json() == {}
    assert response.status_code == 200

    new_schemas_resp = client.get("/registry/schemas")
    assert new_schemas_resp.status_code == 200
    new_schemas = new_schemas_resp.json()
    assert "string:string:string" in new_schemas

    response = client.post(
        "/registry/schemas/idonotexist",
        headers={"content-type": "application/json", "accept": "application/json"},
        data=payload,
    )
    assert response.status_code == 405
    assert "Cannot update Schema. Schema with ID" in response.json()["detail"]


def test_remove_schema():
    response = client.delete("/registry/schemas/string")
    assert response.json() == {}
    assert response.status_code == 200

    response = client.delete(
        "/registry/schemas/string",
        headers={"content-type": "application/json", "accept": "application/json"},
    )
    assert response.status_code == 404
    assert "Cannot update Schema" in response.json()["detail"]
