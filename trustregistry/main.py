from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from registry import registry_actors, registry_schemas
import crud
import models
from db import get_db
from database import engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(registry_actors.router)
app.include_router(registry_schemas.router)


@app.get("/")
async def root(db: Session = Depends(get_db)):
    db_schemas = crud.get_schemas(db)
    db_actors = crud.get_actors(db)
    schemas_repr = [
        f"{schema.did}:{schema.name}:{schema.version}" for schema in db_schemas
    ]
    return {"actors": db_actors, "schemas": schemas_repr}


@app.get("/registry")
async def registry(db: Session = Depends(get_db)):
    return await root(db)
