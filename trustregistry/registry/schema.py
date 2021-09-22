import logging
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel, validator

logger = logging.getLogger(__name__)

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


@router.post("")
async def register_schema(schema: SchemaRegister):
    return schema.dict()


@router.put("/{schema_id}")
async def update_schema(schema_id: str, schema: SchemaUpdate):
    return schema.dict(), schema_id


@router.delete("/{schema_id}")
async def remove_schema(schema_id: str):
    return schema_id
