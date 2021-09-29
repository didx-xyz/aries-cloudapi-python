import json

import dependencies


def test_dependencies():
    with open(dependencies.REGISTRY_FILE_PATH) as tr:
        registry = json.load(tr)

    assert registry == dependencies.read_registry()
