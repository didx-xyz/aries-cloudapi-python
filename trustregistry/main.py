from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from trustregistry.registry import registry_actors, registry_schemas
from trustregistry import crud
from trustregistry import models
from trustregistry.db import get_db
from trustregistry.database import engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(registry_actors.router)
app.include_router(registry_schemas.router)


@app.get("/")
async def root(db: Session = Depends(get_db)):
    db_schemas = crud.get_schemas(db)
    db_actors = crud.get_actors(db)
    schemas_repr = [
        schema.id for schema in db_schemas
    ]
    return {"actors": db_actors, "schemas": schemas_repr}


@app.get("/registry")
async def registry(db: Session = Depends(get_db)):
    return await root(db)
