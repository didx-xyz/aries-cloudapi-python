import json
import os

ENV = os.getenv("ENV", "test")
if ENV == "prod":
    REGISTRY_FILE_PATH = os.getenv("REGISTRYFILE", "./registryfiles/trustregistry.json")
else:
    REGISTRY_FILE_PATH = "./registryfiles/trustregistry_test.json"


def read_registry():
    with open(REGISTRY_FILE_PATH, "r", encoding="utf-8") as json_file:
        json_data = json.load(json_file)
    return dict(json_data)
