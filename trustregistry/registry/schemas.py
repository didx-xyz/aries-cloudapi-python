import json
import os

from dependencies import read_registry

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from pydantic import BaseModel

ENV = os.getenv("ENV", "test")
if ENV == "prod":
    REGISTRY_FILE_PATH = os.getenv("REGISTRYFILE", "./registryfiles/trustregistry.json")
else:
    REGISTRY_FILE_PATH = "./registryfiles/trustregistry_test.json"

router = APIRouter(prefix="/registry/schemas", tags=["schema"])


class Schema(BaseModel):
    did: str
    name: str
    version: str


def _write_registry(data, filepath: str = REGISTRY_FILE_PATH):
    with open(filepath, "w") as tr:
        json.dump(data, tr, ensure_ascii=False, indent=4)


def _schema_exists(schema_id: str, schema_list: list):
    schema_ids_old = [schema.split(":")[0] for schema in schema_list]
    return schema_id in schema_ids_old


@router.get("/")
async def get_schemas(register=Depends(read_registry)):
    return register["schemas"]


@router.post("/")
async def register_schema(new_schema: Schema, register=Depends(read_registry)):
    if _schema_exists(new_schema.did, register["schemas"]):
        raise HTTPException(
            status_code=405, detail=f"Schema with ID {new_schema.did} already exists"
        )
    register["schemas"].append(":".join(new_schema.dict().values()))
    _write_registry(register)
    return {}


@router.post("/{schema_id}")
async def update_schema(
    schema_id: str, new_schema: Schema, register=Depends(read_registry)
):
    if not _schema_exists(schema_id, register["schemas"]):
        raise HTTPException(
            status_code=405,
            detail=f"Cannot update Schema. Schema with ID {new_schema.did} does not exists.",
        )
    for schema in register["schemas"]:
        schema_id_old = schema.split(":")[0]
        if new_schema.did == schema_id_old:
            schema = ":".join(new_schema.dict().values())
    _write_registry(register)
    return {}


@router.delete("/{schema_id}")
async def remove_schema(schema_id: str, register=Depends(read_registry)):
    if not _schema_exists(schema_id, register["schemas"]):
        raise HTTPException(
            status_code=404,
            detail=f"Cannot update Schema. Schema with ID {schema_id} does not exists.",
        )
    for i, schema in enumerate(register["schemas"]):
        schema_id_old = schema.split(":")[0]
        if schema_id == schema_id_old:
            del register["schemas"][i]
    _write_registry(register)
    return {}
