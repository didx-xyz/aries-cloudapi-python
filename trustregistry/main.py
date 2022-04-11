from fastapi import FastAPI, Depends
from typing import Optional
from sqlalchemy.orm import Session
import os

from trustregistry.registry import registry_actors, registry_schemas
from trustregistry import crud
from trustregistry import models
from trustregistry.db import get_db
from trustregistry.database import engine
from trustregistry.utils import get_data_slice

OPENAPI_NAME = os.getenv("OPENAPI_NAME", "Trust Registry")
PROJECT_VERSION = os.getenv("PROJECT_VERSION", "0.0.1BETA")
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=OPENAPI_NAME,
    description="Welcome to the OpenAPI interface to the Aries CloudAPI trust registry",
    version=PROJECT_VERSION,
)

app.include_router(registry_actors.router)
app.include_router(registry_schemas.router)


@app.get("/")
async def root(
    actor_start: Optional[int] = None,
    actor_end: Optional[int] = None,
    schema_start: Optional[int] = None,
    schema_end: Optional[int] = None,
    db: Session = Depends(get_db),
):
    db_schemas = crud.get_schemas(db)
    db_actors = crud.get_actors(db)
    schemas_repr = [schema.id for schema in db_schemas]
    schemas = get_data_slice(schemas_repr, schema_start, schema_end)
    actors = get_data_slice(db_actors, actor_start, actor_end)
    return {"actors": actors, "schemas": schemas}


@app.get("/registry")
async def registry(db: Session = Depends(get_db)):
    return await root(db=db)
