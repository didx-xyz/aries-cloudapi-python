import json

from . import test_main
from trustregistry.registry.registry_schemas import _get_schema_attrs, SchemaID

client = test_main.client


def test_get_schemas():
    response = client.get("/registry/schemas")
    assert response.status_code == 200
    assert response.json() == {"schemas": []}


def test_register_schema():
    schema_dict = {"did": "string:2", "name": "string", "version": "string"}
    schema_id = ":".join(schema_dict.values())
    payload = json.dumps({"schema_id": schema_id})
    response = client.post(
        "/registry/schemas/",
        headers={"content-type": "application/json", "accept": "application/json"},
        data=payload,
    )
    schema_dict["id"] = schema_id
    schema_dict["did"] = "string"
    assert response.json() == schema_dict
    assert response.status_code == 200

    new_schemas_resp = client.get("/registry/schemas")
    assert new_schemas_resp.status_code == 200
    new_schemas = new_schemas_resp.json()
    assert "string:2:string:string" in new_schemas["schemas"]

    response = client.post(
        "/registry/schemas/",
        headers={"content-type": "application/json", "accept": "application/json"},
        data=payload,
    )
    assert response.status_code == 405
    assert "Schema already exists" in response.json()["detail"]


def test_update_schema():
    schema_dict = {
        "did": "string_updated:2",
        "name": "string_updated",
        "version": "string_updated",
    }
    schema_id = ":".join(schema_dict.values())
    payload = json.dumps({"schema_id": schema_id})
    response = client.post(
        "/registry/schemas/string:2:string:string",
        headers={"content-type": "application/json", "accept": "application/json"},
        data=payload,
    )
    schema_dict["id"] = schema_id
    schema_dict["did"] = "string_updated"
    assert response.json() == schema_dict
    assert response.status_code == 200

    new_schemas_resp = client.get("/registry/schemas")
    assert new_schemas_resp.status_code == 200
    new_schemas = new_schemas_resp.json()
    assert schema_id in new_schemas["schemas"]

    response = client.post(
        "/registry/schemas/i:donot:exist",
        headers={"content-type": "application/json", "accept": "application/json"},
        data=payload,
    )
    assert response.status_code == 405
    assert "Schema not found" in response.json()["detail"]


def test_remove_schema():
    response = client.delete(
        "/registry/schemas/string_updated:2:string_updated:string_updated"
    )
    assert response.status_code == 200
    assert response.json() is None

    response = client.delete(
        "/registry/schemas/string_updated:2:string_updated:string_updated",
        headers={"content-type": "application/json", "accept": "application/json"},
    )
    assert response.status_code == 404
    assert "Schema not found" in response.json()["detail"]


def test__get_schema_attrs():
    res = _get_schema_attrs(schema_id=SchemaID(schema_id="abc:2:Peter Parker:0.4.20"))

    assert res == ["abc:2", "Peter Parker", "0.4.20"]

    res = _get_schema_attrs(schema_id=SchemaID(schema_id="abc:Peter Parker:0.4.20"))

    assert res == ["abc", "Peter Parker", "0.4.20"]
