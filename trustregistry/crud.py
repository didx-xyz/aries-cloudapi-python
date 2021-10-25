from typing import List

from sqlalchemy.orm import Session

from trustregistry import models, schemas


def get_actors(db: Session, skip: int = 0, limit: int = 1000) -> List[models.Actor]:
    return db.query(models.Actor).offset(skip).limit(limit).all()


def create_actor(db: Session, actor: schemas.Actor) -> models.Actor:
    db_actor = db.query(models.Actor).filter(models.Actor.id == actor.id).one_or_none()
    if db_actor is not None:
        return None
    db_actor = models.Actor(**actor.dict())
    db.add(db_actor)
    db.commit()
    db.refresh(db_actor)
    return db_actor


def delete_actor(db: Session, actor_id: str) -> models.Actor:
    db_actor = db.query(models.Actor).filter(models.Actor.id == actor_id).one_or_none()
    if db_actor is None:
        return None
    db.delete(db_actor)
    db.commit()
    return db_actor


def update_actor(db: Session, actor: schemas.Actor, actor_id=str) -> models.Actor:
    db_actor = db.query(models.Actor).filter(models.Actor.id == actor_id).one_or_none()
    if db_actor is None:
        return None

    for var, value in vars(actor).items():
        setattr(db_actor, var, value) if value else None

    db.add(db_actor)
    db.commit()
    db.refresh(db_actor)
    return db_actor


def get_schemas(db: Session, skip: int = 0, limit: int = 1000) -> List[models.Schema]:
    return db.query(models.Schema).offset(skip).limit(limit).all()


def create_schema(db: Session, schema: schemas.Schema) -> models.Schema:
    db_schema = (
        db.query(models.Schema).filter(models.Schema.id == schema.id).one_or_none()
    )
    if db_schema is not None:
        return 1
    db_schema = models.Schema(**schema.dict())
    db.add(db_schema)
    db.commit()
    db.refresh(db_schema)
    return db_schema


def update_schema(db: Session, schema: schemas.Schema, schema_id: str) -> models.Schema:
    db_schema = (
        db.query(models.Schema).filter(models.Schema.id == schema_id).one_or_none()
    )
    if db_schema is None:
        return None

    for var, value in vars(schema).items():
        setattr(db_schema, var, value) if value else None

    db.add(db_schema)
    db.commit()
    db.refresh(db_schema)
    return db_schema


def delete_schema(db: Session, schema_id: str) -> models.Schema:
    db_schema = (
        db.query(models.Schema).filter(models.Schema.id == schema_id).one_or_none()
    )
    if db_schema is None:
        return None
    db.delete(db_schema)
    db.commit()
    return db_schema
