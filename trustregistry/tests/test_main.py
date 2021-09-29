import json

from fastapi.testclient import TestClient

import main
import dependencies

client = TestClient(main.app)

with open(dependencies.REGISTRY_FILE_PATH) as tr:
    registry = json.load(tr)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == registry


def test_registry():
    response = client.get("/registry")
    assert response.status_code == 200
    assert response.json() == registry
