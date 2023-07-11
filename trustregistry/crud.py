from typing import List

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from shared.log_config import get_logger
from trustregistry import db
from shared.models.trustregistry import Actor, Schema

logger = get_logger(__name__)


def get_actors(db_session: Session, skip: int = 0, limit: int = 1000) -> List[db.Actor]:
    logger.info("Querying all actors from database")
    result = db_session.query(db.Actor).offset(skip).limit(limit).all()

    if result:
        logger.info("Successfully retrieved `{}` actors from database.", len(result))
    else:
        logger.warning("No actors retrieved from database.")

    return result


def get_actor_by_did(db_session: Session, actor_did: str) -> db.Actor:
    bound_logger = logger.bind(body={"actor_did": actor_did})
    bound_logger.info("Querying actor by DID")
    result = db_session.query(db.Actor).filter(db.Actor.did == actor_did).first()

    if result:
        bound_logger.info("Successfully retrieved actor from database.")
    else:
        bound_logger.info("Actor DID not found.")
        raise ActorDoesNotExistException

    return result


def get_actor_by_id(db_session: Session, actor_id: str) -> db.Actor:
    bound_logger = logger.bind(body={"actor_id": actor_id})
    bound_logger.info("Querying actor by ID")
    result = db_session.query(db.Actor).filter(db.Actor.id == actor_id).first()

    if result:
        bound_logger.info("Successfully retrieved actor from database.")
    else:
        bound_logger.info("Actor ID not found.")
        raise ActorDoesNotExistException

    return result


def create_actor(db_session: Session, actor: Actor) -> db.Actor:
    bound_logger = logger.bind(body={"actor": actor})
    bound_logger.info("Try to create actor in database")

    try:
        bound_logger.debug("Adding actor to database")
        db_actor = db.Actor(**actor.dict())
        db_session.add(db_actor)
        db_session.commit()
        db_session.refresh(db_actor)

        bound_logger.info("Successfully added actor to database.")
        return db_actor

    except IntegrityError as e:
        db_session.rollback()
        constraint_violation = str(e.orig).lower()

        if f"actors.id" in constraint_violation:
            bound_logger.info(
                "Bad request: The requested actor ID already exists in database."
            )
            raise ActorAlreadyExistsException(
                f"Bad request: The requested actor ID: `{actor.id}` already exists in database."
            )

        elif f"{actor.did}" in constraint_violation:
            bound_logger.info(
                "The requested actor DID: {} already exists in database.", actor.did
            )
            raise ActorAlreadyExistsException

        elif f"{actor.didcomm_invitation}" in constraint_violation:
            bound_logger.info(
                "The requested actor DIDComm invitation: {} already exists in database.",
                actor.didcomm_invitation,
            )
            raise ActorAlreadyExistsException

def delete_actor(db_session: Session, actor_id: str) -> db.Actor:
    bound_logger = logger.bind(body={"actor_id": actor_id})
    bound_logger.info("Delete actor from database. First assert actor ID exists")
    db_actor = db_session.query(db.Actor).filter(db.Actor.id == actor_id).one_or_none()

    if not db_actor:
        bound_logger.info("Requested actor ID to delete does not exist in database.")
        raise ActorDoesNotExistException

    bound_logger.debug("Deleting actor")
    db_session.delete(db_actor)
    db_session.commit()

    bound_logger.info("Successfully deleted actor ID.")
    return db_actor


def update_actor(db_session: Session, actor: Actor) -> db.Actor:
    bound_logger = logger.bind(body={"actor": actor})
    bound_logger.info("Update actor in database. First assert actor ID exists")
    db_actor = db_session.query(db.Actor).filter(db.Actor.id == actor.id).one_or_none()

    if not db_actor:
        bound_logger.info("Requested actor ID to update does not exist in database.")
        raise ActorDoesNotExistException

    bound_logger.debug("Updating actor")
    for var, value in vars(actor).items():
        setattr(db_actor, var, value)

    db_session.add(db_actor)
    db_session.commit()
    db_session.refresh(db_actor)

    bound_logger.info("Successfully updated actor.")
    return db_actor


def get_schemas(
    db_session: Session, skip: int = 0, limit: int = 1000
) -> List[db.Schema]:
    logger.debug("Query all schemas from database")
    result = db_session.query(db.Schema).offset(skip).limit(limit).all()

    if result:
        logger.info("Successfully retrieved {} schemas from database.", len(result))
    else:
        logger.warning("No schemas retrieved from database.")

    return result


def get_schema_by_id(db_session: Session, schema_id: str) -> db.Schema:
    bound_logger = logger.bind(body={"schema_id": schema_id})
    bound_logger.info("Querying for schema by ID")
    result = db_session.query(db.Schema).filter(db.Schema.id == schema_id).one_or_none()

    if result:
        bound_logger.info("Successfully retrieved schema from database.")
    else:
        bound_logger.info("Schema does not exist in database.")
        raise SchemaDoesNotExistException

    return result


def create_schema(db_session: Session, schema: Schema) -> db.Schema:
    bound_logger = logger.bind(body={"schema": schema})
    bound_logger.info(
        "Create schema in database. First assert schema ID does not already exist"
    )
    db_schema = (
        db_session.query(db.Schema).filter(db.Schema.id == schema.id).one_or_none()
    )

    if db_schema:
        bound_logger.info("The requested schema ID already exists in database.")
        raise SchemaAlreadyExistsException

    bound_logger.debug("Adding schema to database")
    db_schema = db.Schema(**schema.dict())
    db_session.add(db_schema)
    db_session.commit()
    db_session.refresh(db_schema)

    bound_logger.info("Successfully added schema to database.")
    return db_schema


def update_schema(db_session: Session, schema: Schema, schema_id: str) -> db.Schema:
    bound_logger = logger.bind(body={"schema": schema, "schema_id": schema_id})
    bound_logger.info("Update schema in database. First assert schema ID exists")
    db_schema = (
        db_session.query(db.Schema).filter(db.Schema.id == schema_id).one_or_none()
    )

    if not db_schema:
        bound_logger.debug(
            "Requested to update a schema that does not exist in database."
        )
        raise SchemaDoesNotExistException

    bound_logger.debug("Updating schema on database")
    for var, value in vars(schema).items():
        setattr(db_schema, var, value) if value else None

    db_session.add(db_schema)
    db_session.commit()
    db_session.refresh(db_schema)

    bound_logger.info("Successfully updated schema on database.")
    return db_schema


def delete_schema(db_session: Session, schema_id: str) -> db.Schema:
    bound_logger = logger.bind(body={"schema_id": schema_id})
    bound_logger.info("Delete schema from database. First assert schema ID exists")
    db_schema = (
        db_session.query(db.Schema).filter(db.Schema.id == schema_id).one_or_none()
    )

    if not db_schema:
        raise SchemaDoesNotExistException

    bound_logger.debug("Deleting schema from database")
    db_session.delete(db_schema)
    db_session.commit()

    bound_logger.info("Successfully deleted schema from database.")
    return db_schema


class ActorAlreadyExistsException(Exception):
    """Raised when attempting to create an actor that already exists in the database."""

    def __init__(self, message):
        self.message = message


class ActorDoesNotExistException(Exception):
    """Raised when attempting to delete or update an actor that does not exist in the database."""


class SchemaAlreadyExistsException(Exception):
    """Raised when attempting to create a schema that already exists in the database."""


class SchemaDoesNotExistException(Exception):
    """Raised when attempting to delete or update a schema that does not exist in the database."""
