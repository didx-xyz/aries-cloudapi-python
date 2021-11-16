from typing import List
from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from trustregistry import crud
from trustregistry.db import get_db
from trustregistry.schemas import Schema

router = APIRouter(prefix="/registry/schemas", tags=["schema"])

class GetSchemasResponse(BaseModel):
    schemas: List[str]

class SchemaID(BaseModel):
    schema_id: str = Field(..., example="WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0")


@router.get("/", response_model=GetSchemasResponse)
async def get_schemas(db: Session = Depends(get_db)) -> GetSchemasResponse:
    db_schemas = crud.get_schemas(db)
    schemas_repr = [schema.id for schema in db_schemas]
    return GetSchemasResponse(schemas=schemas_repr)

@router.post("/")
async def register_schema(schema_id: SchemaID, db: Session = Depends(get_db)) -> Schema:
    schema_attrs_list = _get_schema_attrs(schema_id)
    create_schema_res = crud.create_schema(
        db,
        schema=Schema(
            did=schema_attrs_list[0],
            name=schema_attrs_list[2],
            version=schema_attrs_list[3],
            id=schema_id.schema_id,
        ),
    )
    if create_schema_res == 1:
        raise HTTPException(status_code=405, detail="Schema already exists")
    return create_schema_res


@router.put("/{schema_id}")
async def update_schema(
    schema_id: str, new_schema_id: SchemaID, db: Session = Depends(get_db)
) -> Schema:
    schema_attrs_list = _get_schema_attrs(new_schema_id)
    update_schema_res = crud.update_schema(
        db,
        schema=Schema(
            did=schema_attrs_list[0],
            name=schema_attrs_list[2],
            version=schema_attrs_list[3],
            id=new_schema_id.schema_id,
        ),
        schema_id=schema_id,
    )
    if update_schema_res is None:
        raise HTTPException(
            status_code=405,
            detail="Schema not found",
        )
    return update_schema_res


@router.delete("/{schema_id}", status_code=204)
async def remove_schema(schema_id: str, db: Session = Depends(get_db)) -> None:
    delete_scheme_res = crud.delete_schema(db, schema_id=schema_id)
    if delete_scheme_res is None:
        raise HTTPException(
            status_code=404,
            detail="Schema not found.",
        )


def _get_schema_attrs(schema_id: SchemaID) -> List[str]:
    # Split from the back because DID may contain a colon
    return schema_id.schema_id.split(":", 3)
