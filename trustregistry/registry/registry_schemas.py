from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from trustregistry import crud
from trustregistry.db import get_db
from trustregistry.schemas import Schema

router = APIRouter(prefix="/registry/schemas", tags=["schema"])


class SchemaID(BaseModel):
    schema_id: str = Field("did:name:version")


@router.get("/")
async def get_schemas(db: Session = Depends(get_db)):
    db_schemas = crud.get_schemas(db)
    # This is the same as id field now.
    schemas_repr = [schema.id for schema in db_schemas]
    return {"schemas": schemas_repr}


@router.post("/")
async def register_schema(schema_id: SchemaID, db: Session = Depends(get_db)):
    schema_attrs_list = _get_schema_attrs(
        schema_id
    )  # Split from the back bacause did can contain a colon
    create_schema_res = crud.create_schema(
        db,
        schema=Schema(
            did=schema_attrs_list[0],
            name=schema_attrs_list[1],
            version=schema_attrs_list[2],
        ),
    )
    if create_schema_res == 1:
        raise HTTPException(status_code=405, detail="Schema already exists")
    return create_schema_res


@router.post("/{schema_id}")
async def update_schema(
    schema_id: str, new_schema_id: SchemaID, db: Session = Depends(get_db)
):
    schema_attrs_list = _get_schema_attrs(
        new_schema_id
    )  # Split from the back bacause did can contain a colon
    update_schema_res = crud.update_schema(
        db,
        schema=Schema(
            did=schema_attrs_list[0],
            name=schema_attrs_list[-2],
            version=schema_attrs_list[-1],
        ),
        schema_id=schema_id,
    )
    if update_schema_res is None:
        raise HTTPException(
            status_code=405,
            detail="Schema not found",
        )
    return update_schema_res


@router.delete("/{schema_id}")
async def remove_schema(schema_id: str, db: Session = Depends(get_db)):
    delete_scheme_res = crud.delete_schema(db, schema_id=schema_id)
    if delete_scheme_res is None:
        raise HTTPException(
            status_code=404,
            detail="Schema not found.",
        )


def _get_schema_attrs(schema_id: SchemaID) -> list:
    return schema_id.schema_id.rsplit(":")
