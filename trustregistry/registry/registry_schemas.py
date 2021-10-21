from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from sqlalchemy.orm import Session

import crud
from db import get_db
from schemas import Schema

router = APIRouter(prefix="/registry/schemas", tags=["schema"])


@router.get("/")
async def get_schemas(db: Session = Depends(get_db)):
    db_schemas = crud.get_schemas(db)
    # This is the same as id field now.
    schemas_repr = [
        f"{schema.did}:{schema.name}:{schema.version}" for schema in db_schemas
    ]
    return {"schemas": schemas_repr}


@router.post("/")
async def register_schema(schema: Schema, db: Session = Depends(get_db)):
    create_schema_res = crud.create_schema(db, schema=schema)
    if create_schema_res == 1:
        raise HTTPException(status_code=405, detail="Schema already exists")
    return create_schema_res


@router.post("/{schema_id}")
async def update_schema(schema_id: str, schema: Schema, db: Session = Depends(get_db)):
    update_schema_res = crud.update_schema(db, schema=schema, schema_id=schema_id)
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
