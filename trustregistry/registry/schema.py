import json

from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel, validator

router = APIRouter(prefix="/registry/schema", tags=["schema"])


class SchemaBase(BaseModel):
    id: str


class SchemaUpdate(BaseModel):
    did: Optional[str] = None
    name: Optional[str] = None
    version: Optional[str] = None


class SchemaRegister(SchemaUpdate, SchemaBase):
    @validator("did", always=True)
    def set_did(cls, value, values):
        return values["id"].split(":")[0]

    @validator("name", always=True)
    def set_name(cls, value, values):
        return values["id"].split(":")[1]

    @validator("version", always=True)
    def set_version(cls, value, values):
        return values["id"].split(":")[2]


@router.post("/")
async def register_schema(new_schema: SchemaRegister):
    with open("./registryfiles/trustregistry.json", "r+") as tr:
        registry_file = json.load(tr)
        registry_file["schemas"].append(sum(new_schema.dict().values()))
        tr.write(json.dumps(registry_file))
    return {}


@router.put("/{schema_id}")
async def update_schema(schema_id: str, new_schema: SchemaUpdate):
    with open("./registryfiles/trustregistry.json", "r+") as tr:
        registry_file = json.load(tr)
        for schema in registry_file["schemas"]:
            schema_id_old = schema.split(":")[0]
            if schema_id == schema_id_old:
                schema = new_schema
        tr.write(json.dumps(registry_file))
    return {}


@router.delete("/{schema_id}")
async def remove_schema(schema_id: str):
    with open("./registryfiles/trustregistry.json", "r+") as tr:
        registry_file = json.load(tr)
        for i, schema in enumerate(registry_file["schemas"]):
            schema_id_old = schema.split(":")[0]
            if schema_id == schema_id_old:
                del registry_file["schemas"][i]
        tr.write(json.dumps(registry_file))
    return {}
