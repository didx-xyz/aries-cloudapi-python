import os

from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from trustregistry import crud, models
from trustregistry.config.log_config import get_logger
from trustregistry.database import engine
from trustregistry.db import get_db
from trustregistry.registry import registry_actors, registry_schemas

logger = get_logger(__name__)

OPENAPI_NAME = os.getenv("OPENAPI_NAME", "Trust Registry")
PROJECT_VERSION = os.getenv("PROJECT_VERSION", "0.0.1BETA")


def create_app():
    application = FastAPI(
        title=OPENAPI_NAME,
        version=PROJECT_VERSION,
        description="Welcome to the OpenAPI interface to the Aries CloudAPI trust registry",
    )
    application.include_router(registry_actors.router)
    application.include_router(registry_schemas.router)
    return application


app = create_app()


@app.on_event("startup")
async def startup_event():
    models.Base.metadata.create_all(bind=engine)
    engine.dispose()

    # Validate tables are created
    with engine.connect() as connection:
        result = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table';"
        )
        logger.debug("TrustRegistry tables created: %s", [row[0] for row in result])


@app.get("/")
async def root(db: Session = Depends(get_db)):
    db_schemas = crud.get_schemas(db)
    db_actors = crud.get_actors(db)
    schemas_repr = [schema.id for schema in db_schemas]
    return {"actors": db_actors, "schemas": schemas_repr}


@app.get("/registry")
async def registry(db: Session = Depends(get_db)):
    return await root(db)
