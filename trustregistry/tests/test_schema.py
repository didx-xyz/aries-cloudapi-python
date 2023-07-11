import pytest
from httpx import AsyncClient

from shared import TRUST_REGISTRY_URL
from trustregistry.registry.registry_schemas import SchemaID, _get_schema_attrs

schema_id = "string:2:string:string"
updated_schema_id = "string_updated:2:string_updated:string_updated"


@pytest.mark.anyio
async def test_get_schemas():
    async with AsyncClient() as client:
        response = await client.get(f"{TRUST_REGISTRY_URL}/registry/schemas")
    assert response.status_code == 200
    assert "schemas" in response.json()


@pytest.mark.anyio
async def test_register_schema():
    schema_dict = {
        "id": schema_id,
        "did": "string",
        "name": "string",
        "version": "string",
    }
    payload = {"schema_id": schema_id}

    async with AsyncClient() as client:
        response = await client.post(
            f"{TRUST_REGISTRY_URL}/registry/schemas",
            json=payload,
        )

        assert response.json() == schema_dict
        assert response.status_code == 200

        new_schemas_resp = await client.get(
            f"{TRUST_REGISTRY_URL}/registry/schemas/{schema_id}"
        )
        assert new_schemas_resp.status_code == 200
        new_schema = new_schemas_resp.json()
        assert schema_id == new_schema["id"]

        response = await client.post(
            f"{TRUST_REGISTRY_URL}/registry/schemas",
            json=payload,
        )
        assert response.status_code == 405
        assert "Schema already exists" in response.json()["detail"]


@pytest.mark.anyio
async def test_get_schema_by_id():
    schema_dict = {
        "id": schema_id,
        "did": "string",
        "name": "string",
        "version": "string",
    }

    async with AsyncClient() as client:
        response = await client.get(
            f"{TRUST_REGISTRY_URL}/registry/schemas/{schema_id}"
        )
        assert response.json() == schema_dict
        assert response.status_code == 200

        response = await client.get(
            f"{TRUST_REGISTRY_URL}/registry/schemas/i:donot:exist"
        )
        assert response.status_code == 404
        assert "Schema not found" in response.json()["detail"]


@pytest.mark.anyio
async def test_update_schema():
    schema_dict = {
        "id": updated_schema_id,
        "did": "string_updated",
        "name": "string_updated",
        "version": "string_updated",
    }
    payload = {"schema_id": updated_schema_id}

    async with AsyncClient() as client:
        response = await client.put(
            f"{TRUST_REGISTRY_URL}/registry/schemas/{schema_id}",
            json=payload,
        )
        assert response.json() == schema_dict
        assert response.status_code == 200

        updated_schema_response = await client.get(
            f"{TRUST_REGISTRY_URL}/registry/schemas/{updated_schema_id}"
        )
        assert updated_schema_response.status_code == 200
        updated_schema = updated_schema_response.json()
        assert updated_schema_id == updated_schema["id"]

        response = await client.put(
            f"{TRUST_REGISTRY_URL}/registry/schemas/i:donot:exist",
            json=payload,
        )
        assert response.status_code == 405
        assert "Schema not found" in response.json()["detail"]


@pytest.mark.anyio
async def test_remove_schema():
    async with AsyncClient() as client:
        response = await client.delete(
            f"{TRUST_REGISTRY_URL}/registry/schemas/{updated_schema_id}"
        )
        assert response.status_code == 204
        assert not response.text

        response = await client.delete(
            f"{TRUST_REGISTRY_URL}/registry/schemas/{updated_schema_id}"
        )
        assert response.status_code == 404
        assert "Schema not found" in response.json()["detail"]


@pytest.mark.anyio
async def test__get_schema_attrs():
    res = _get_schema_attrs(schema_id=SchemaID(schema_id="abc:2:Peter Parker:0.4.20"))

    assert res == ["abc", "2", "Peter Parker", "0.4.20"]
