from typing import List

from sqlalchemy.orm import Session

from shared.log_config import get_logger
from trustregistry.models import DB_Actor, DB_Schema
from trustregistry.schemas import Actor, Schema

logger = get_logger(__name__)


def get_actors(db: Session, skip: int = 0, limit: int = 1000) -> List[DB_Actor]:
    logger.info("Querying all actors from database")
    result = db.query(DB_Actor).offset(skip).limit(limit).all()

    if result:
        logger.info("Successfully retrieved `{}` actors from database.", len(result))
    else:
        logger.warning("No actors retrieved from database.")

    return result


def get_actor_by_did(db: Session, actor_did: str) -> DB_Actor:
    bound_logger = logger.bind(body={"actor_did": actor_did})
    bound_logger.info("Querying actor by DID")
    result = db.query(DB_Actor).filter(DB_Actor.did == actor_did).first()

    if result:
        bound_logger.info("Successfully retrieved actor from database.")
    else:
        bound_logger.info("Actor DID not found.")
        raise ActorDoesNotExistException

    return result

def get_actor_by_id(db: Session, actor_id: str) -> DB_Actor:
    bound_logger = logger.bind(body={"actor_id": actor_id})
    bound_logger.info("Querying actor by ID")
    result = db.query(DB_Actor).filter(DB_Actor.id == actor_id).first()

    if result:
        bound_logger.info("Successfully retrieved actor from database.")
    else:
        bound_logger.info("Actor ID not found.")
        raise ActorDoesNotExistException

    return result


def create_actor(db: Session, actor: Actor) -> DB_Actor:
    bound_logger = logger.bind(body={"actor": actor})
    bound_logger.info(
        "Create actor in database. First assert actor ID does not already exist"
    )
    db_actor = db.query(DB_Actor).filter(DB_Actor.id == actor.id).one_or_none()

    if db_actor:
        bound_logger.info(
            "Cannot create actor, as actor ID `{}` already exists in database.",
            actor.id,
        )
        raise ActorAlreadyExistsException

    bound_logger.debug("Adding actor to database")
    db_actor = DB_Actor(**actor.dict())
    db.add(db_actor)
    db.commit()
    db.refresh(db_actor)

    bound_logger.info("Successfully added actor to database.")
    return db_actor


def delete_actor(db: Session, actor_id: str) -> DB_Actor:
    bound_logger = logger.bind(body={"actor_id": actor_id})
    bound_logger.info("Delete actor from database. First assert actor ID exists")
    db_actor = db.query(DB_Actor).filter(DB_Actor.id == actor_id).one_or_none()

    if not db_actor:
        bound_logger.info("Requested actor ID to delete does not exist in database.")
        raise ActorDoesNotExistException

    bound_logger.debug("Deleting actor")
    db.delete(db_actor)
    db.commit()

    bound_logger.info("Successfully deleted actor ID.")
    return db_actor


def update_actor(db: Session, actor: Actor) -> DB_Actor:
    bound_logger = logger.bind(body={"actor": actor})
    bound_logger.info("Update actor in database. First assert actor ID exists")
    db_actor = db.query(DB_Actor).filter(DB_Actor.id == actor.id).one_or_none()

    if not db_actor:
        bound_logger.info("Requested actor ID to update does not exist in database.")
        raise ActorDoesNotExistException

    bound_logger.debug("Updating actor")
    for var, value in vars(actor).items():
        setattr(db_actor, var, value)

    db.add(db_actor)
    db.commit()
    db.refresh(db_actor)

    bound_logger.info("Successfully updated actor.")
    return db_actor


def get_schemas(db: Session, skip: int = 0, limit: int = 1000) -> List[DB_Schema]:
    logger.debug("Query all schemas from database")
    result = db.query(DB_Schema).offset(skip).limit(limit).all()

    if result:
        logger.info("Successfully retrieved {} schemas from database.", len(result))
    else:
        logger.warning("No schemas retrieved from database.")

    return result

def get_schema_by_id(db: Session, schema_id: str) -> DB_Schema:
    bound_logger = logger.bind(body={"schemaID": schema_id})
    bound_logger.info("Querying for schema by ID")
    result = db.query(DB_Schema).filter(DB_Schema.id == schema_id).one_or_none()

    if result:
        bound_logger.info("Successfully retrieved schema from database.")
    else:
        bound_logger.info("Schema does not exist in database.")
        raise SchemaDoesNotExistException

    return result    

def create_schema(db: Session, schema: Schema) -> DB_Schema:
    bound_logger = logger.bind(body={"schema": schema})
    bound_logger.info(
        "Create schema in database. First assert schema ID does not already exist"
    )
    db_schema = (
        db.query(DB_Schema).filter(DB_Schema.id == schema.id).one_or_none()
    )

    if db_schema:
        bound_logger.info("The requested schema ID already exists in database.")
        raise SchemaAlreadyExistsException

    bound_logger.debug("Adding schema to database")
    db_schema = DB_Schema(**schema.dict())
    db.add(db_schema)
    db.commit()
    db.refresh(db_schema)

    bound_logger.info("Successfully added schema to database.")
    return db_schema


def update_schema(db: Session, schema: Schema, schema_id: str) -> DB_Schema:
    bound_logger = logger.bind(body={"schema": schema, "schema_id": schema_id})
    bound_logger.info("Update schema in database. First assert schema ID exists")
    db_schema = (
        db.query(DB_Schema).filter(DB_Schema.id == schema_id).one_or_none()
    )

    if not db_schema:
        bound_logger.debug(
            "Requested to update a schema that does not exist in database."
        )
        raise SchemaDoesNotExistException

    bound_logger.debug("Updating schema on database")
    for var, value in vars(schema).items():
        setattr(db_schema, var, value) if value else None

    db.add(db_schema)
    db.commit()
    db.refresh(db_schema)

    bound_logger.info("Successfully updated schema on database.")
    return db_schema


def delete_schema(db: Session, schema_id: str) -> DB_Schema:
    bound_logger = logger.bind(body={"schema_id": schema_id})
    bound_logger.info("Delete schema from database. First assert schema ID exists")
    db_schema = (
        db.query(DB_Schema).filter(DB_Schema.id == schema_id).one_or_none()
    )

    if not db_schema:
        raise SchemaDoesNotExistException

    bound_logger.debug("Deleting schema from database")
    db.delete(db_schema)
    db.commit()

    bound_logger.info("Successfully deleted schema from database.")
    return db_schema


class ActorAlreadyExistsException(Exception):
    """Raised when attempting to create an actor that already exists in the database."""


class ActorDoesNotExistException(Exception):
    """Raised when attempting to delete or update an actor that does not exist in the database."""


class SchemaAlreadyExistsException(Exception):
    """Raised when attempting to create a schema that already exists in the database."""


class SchemaDoesNotExistException(Exception):
    """Raised when attempting to delete or update a schema that does not exist in the database."""
