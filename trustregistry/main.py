from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
import os

from trustregistry.registry import registry_actors, registry_schemas
from trustregistry import crud
from trustregistry import models
from trustregistry.db import get_db
from trustregistry.database import engine

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
async def root(db: Session = Depends(get_db)):
    db_schemas = crud.get_schemas(db)
    db_actors = crud.get_actors(db)
    schemas_repr = [schema.id for schema in db_schemas]
    return {"actors": db_actors, "schemas": schemas_repr}


@app.get("/registry")
async def registry(db: Session = Depends(get_db)):
    return await root(db)
