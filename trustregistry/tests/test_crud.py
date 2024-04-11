from unittest.mock import Mock, patch

import pytest
from sqlalchemy import ScalarResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shared.models.trustregistry import Actor, Schema
from trustregistry import crud, db
from trustregistry.crud import (
    ActorAlreadyExistsException,
    ActorDoesNotExistException,
    SchemaAlreadyExistsException,
    SchemaDoesNotExistException,
)

# pylint: disable=redefined-outer-name


@pytest.fixture
def db_session_mock():
    session = Mock(spec=Session)
    return session


@pytest.mark.anyio
@pytest.mark.parametrize(
    "expected, skip, limit",
    [
        ([db.Actor(id="1", name="Alice"), db.Actor(id="2", name="Bob")], 0, 1000),
        ([], 0, 1000),
        ([db.Actor(id="1", name="Alice"), db.Actor(id="2", name="Bob")], 0, 2),
    ],
)
def test_get_actors(db_session_mock: Session, expected, skip, limit):
    db_session_mock.scalars.return_value.all.return_value = expected

    with patch("trustregistry.crud.select") as select_mock:

        actors = crud.get_actors(db_session_mock, skip=skip, limit=limit)

        db_session_mock.scalars.assert_called()
        assert actors == expected

        select_mock.assert_called_once_with(db.Actor)
        select_mock(db.Actor).offset.assert_called_once_with(skip)
        select_mock(db.Actor).offset(skip).limit.assert_called_once_with(limit)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "expected, actor_did",
    [
        (db.Actor(id="1", name="Alice", did="did:123"), "did:123"),
        (None, "did:notindb"),
    ],
)
def test_get_actor_by_did(db_session_mock: Session, expected, actor_did):
    db_session_mock.scalars.return_value.first.return_value = expected

    with patch("trustregistry.crud.select") as select_mock:

        if expected:
            actor = crud.get_actor_by_did(db_session_mock, actor_did=actor_did)

            db_session_mock.scalars.assert_called()

            assert actor == expected
        else:
            with pytest.raises(ActorDoesNotExistException):
                actor = crud.get_actor_by_did(db_session_mock, actor_did=actor_did)

        select_mock.assert_called_once_with(db.Actor)
        select_mock(
            db.Actor
        ).where.assert_called()  # once_with(db.Actor.did == actor_did)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "expected, actor_name",
    [
        (db.Actor(id="1", name="Alice", did="did:123"), "Alice"),
        (None, "NotInDB"),
    ],
)
def test_get_actor_by_name(db_session_mock: Session, expected, actor_name):
    db_session_mock.scalars.return_value.one_or_none.return_value = expected

    with patch("trustregistry.crud.select") as select_mock:
        if expected:
            result = crud.get_actor_by_name(db_session_mock, actor_name=actor_name)

            db_session_mock.scalars.assert_called()
            assert result == expected
        else:
            with pytest.raises(ActorDoesNotExistException):
                result = crud.get_actor_by_name(db_session_mock, actor_name=actor_name)

        select_mock.assert_called_once_with(db.Actor)
        select_mock(
            db.Actor
        ).where.assert_called()  # _once_with(db.Actor.name == actor_name)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "expected, actor_id",
    [
        (db.Actor(id="1", name="Alice", did="did:123"), "1"),
        (None, "NotInDB"),
    ],
)
def test_get_actor_by_id(db_session_mock: Session, expected, actor_id):
    db_session_mock.scalars.return_value.first.return_value = expected

    with patch("trustregistry.crud.select") as select_mock:
        if expected:
            result = crud.get_actor_by_id(db_session_mock, actor_id=actor_id)

            db_session_mock.scalars.assert_called()
            assert result == expected
        else:
            with pytest.raises(ActorDoesNotExistException):
                result = crud.get_actor_by_id(db_session_mock, actor_id=actor_id)

        select_mock.assert_called_once_with(db.Actor)
        select_mock(db.Actor).where.assert_called()


@pytest.mark.anyio
def test_create_actor(db_session_mock: Session):
    actor = Actor(id="1", name="Alice", did="did:123", roles=["role1", "role2"])
    db_actor = db.Actor(**actor.model_dump())

    result = crud.create_actor(db_session_mock, actor)

    db_session_mock.add.assert_called()  # _once_with(db_actor)
    db_session_mock.commit.assert_called_once()
    db_session_mock.refresh.assert_called()  # _once_with(db_actor)

    assert result.did == db_actor.did
    assert result.name == db_actor.name
    assert result.roles == db_actor.roles

@pytest.mark.anyio
@pytest.mark.parametrize(
    "orig",
    [
        "actors_pkey",
        "ix_actors_name",
        "ix_actors_didcomm_invitation",
        "ix_actors_did",
        "unkonwn_orig",
    ],
)
def test_create_actor_already_exists(db_session_mock: Session, orig: str):
    actor = Actor(id="1", name="Alice", did="did:123", roles=["role1", "role2"])

    db_session_mock.add.side_effect = IntegrityError(
        orig=orig, params=None, statement=None
    )

    with pytest.raises(ActorAlreadyExistsException):
        crud.create_actor(db_session_mock, actor)


@pytest.mark.anyio
def test_create_actor_exception(db_session_mock: Session):
    actor = Actor(id="1", name="Alice", did="did:123", roles=["role1", "role2"])

    db_session_mock.add.side_effect = Exception("Some error")

    with pytest.raises(Exception):
        crud.create_actor(db_session_mock, actor)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "actor, actor_id",
    [
        (Actor(id="1", name="Alice", did="did:123", roles=["role1", "role2"]), "1"),
        (None, "NotInDB"),
    ],
)
def test_delete_actor(db_session_mock: Session, actor, actor_id):
    db_session_mock.scalars.return_value.one_or_none.return_value = actor
    with patch("trustregistry.crud.select") as select_mock, patch(
        "trustregistry.crud.delete"
    ) as delete_mock:

        if actor:
            result = crud.delete_actor(db_session_mock, actor_id=actor_id)

            select_mock.assert_called_once_with(db.Actor)
            select_mock(
                db.Actor
            ).where.assert_called()  # _once_with(db.Actor.id == actor_id)

            delete_mock.assert_called_once_with(db.Actor)
            delete_mock(
                db.Actor
            ).where.assert_called()  # _once_with(db.Actor.id == actor_id)

            db_session_mock.execute.assert_called_once()
            db_session_mock.commit.assert_called_once()

            assert result == actor
        else:
            with pytest.raises(ActorDoesNotExistException):
                crud.delete_actor(db_session_mock, actor_id=actor_id)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "new_actor, old_actor ",
    [
        (
            Actor(id="1", name="Alice", did="did:123", roles=["role1", "role2"]),
            db.Actor(id="1", name="Bob", did="did:123", roles=["role1", "role2"]),
        ),
        (Actor(id="1", name="Alice", did="did:123", roles=["role1", "role2"]), None),
    ],
)
def test_update_actor(db_session_mock: Session, new_actor: Actor, old_actor: db.Actor):
    actor = db.Actor(**new_actor.model_dump())

    db_session_mock.scalars.return_value.one_or_none.return_value = old_actor

    db_session_mock.scalars.retrun_value = ScalarResult[actor]
    if not old_actor:
        with pytest.raises(ActorDoesNotExistException):
            crud.update_actor(db_session_mock, new_actor)
    else:
        with patch("trustregistry.crud.update") as update_mock:
            result = crud.update_actor(db_session_mock, new_actor)

            update_mock.assert_called_once_with(db.Actor)
            update_mock(db.Actor).where.assert_called()
            update_mock(db.Actor).where().values.assert_called()

            db_session_mock.commit.assert_called_once()

            # assert result == actor


@pytest.mark.anyio
@pytest.mark.parametrize(
    "expected, skip, limit",
    [
        (
            [
                db.Schema(did="did:123", name="schema1", version="1.0"),
                db.Schema(did="did:123", name="schema2", version="1.0"),
            ],
            0,
            1000,
        ),
        ([], 0, 1000),
        (
            [
                db.Schema(did="did:123", name="schema1", version="1.0"),
                db.Schema(did="did:123", name="schema2", version="1.0"),
            ],
            0,
            2,
        ),
    ],
)
def test_get_schemas(db_session_mock: Session, expected, skip, limit):
    db_session_mock.scalars.return_value.all.return_value = expected

    with patch("trustregistry.crud.select") as select_mock:

        schemas = crud.get_schemas(db_session_mock, skip=skip, limit=limit)

        db_session_mock.scalars.assert_called()
        assert schemas == expected

        select_mock.assert_called_once_with(db.Schema)
        select_mock(db.Schema).offset.assert_called_once_with(skip)
        select_mock(db.Schema).offset(skip).limit.assert_called_once_with(limit)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "expected, schema_id",
    [
        (db.Schema(id="123", name="schema1", version="1.0"), "123"),
        (None, "idnotindb"),
    ],
)
def test_get_schema_by_id(db_session_mock: Session, expected, schema_id):
    db_session_mock.scalars.return_value.first.return_value = expected

    with patch("trustregistry.crud.select") as select_mock:

        if expected:
            schema = crud.get_schema_by_id(db_session_mock, schema_id=schema_id)

            db_session_mock.scalars.assert_called()

            assert schema == expected
        else:
            with pytest.raises(SchemaDoesNotExistException):
                schema = crud.get_schema_by_id(db_session_mock, schema_id=schema_id)

        select_mock.assert_called_once_with(db.Schema)
        select_mock(db.Schema).where.assert_called()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "old_schema, new_schema",
    [
        (None, Schema(did="did123", name="schema1", version="1.0")),
        (
            db.Schema(did="did123", name="schema1", version="1.0"),
            Schema(did="did123", name="schema1", version="1.0"),
        ),
    ],
)
def test_create_schema(db_session_mock: Session, old_schema, new_schema):
    schema = db.Schema(**new_schema.model_dump())
    db_session_mock.scalars.return_value.one_or_none.return_value = old_schema
    if old_schema:
        with pytest.raises(SchemaAlreadyExistsException):
            crud.create_schema(db_session_mock, new_schema)
    else:
        result = crud.create_schema(db_session_mock, new_schema)
        db_session_mock.add.assert_called()  # _once_with(schema)
        db_session_mock.commit.assert_called_once()
        db_session_mock.refresh.assert_called()  # _once_with(schema)

        assert result.id == schema.id
        assert result.did == schema.did
        assert result.name == schema.name
        assert result.version == schema.version


@pytest.mark.anyio
@pytest.mark.parametrize(
    "new_schema, old_schema",
    [
        (
            Schema(
                did="did123", name="schema_new", version="1.0", id="did123:2:schema_new:1.0"
            ),
            db.Schema(did="did123", name="schema1", version="1.0", id="did123:2:schema1:1.0"),
        ),
        (
            Schema(
                did="did123", name="schema1", version="1.0", id="did123:2:schema1:1.0"
            ),
            None,
        ),
    ],
)
def test_update_schema(db_session_mock: Session, new_schema, old_schema):
    schema = db.Schema(**new_schema.model_dump())
    db_session_mock.scalars.return_value.one_or_none.return_value = old_schema
    if not old_schema:
        with pytest.raises(SchemaDoesNotExistException):
            crud.update_schema(db_session_mock, new_schema, new_schema.id)
    else:
        with patch("trustregistry.crud.update") as update_mock:
            result = crud.update_schema(db_session_mock, new_schema, new_schema.id)

            update_mock.assert_called_once_with(db.Schema)
            update_mock(db.Schema).where.assert_called()
            update_mock(db.Schema).where().values.assert_called()

            db_session_mock.commit.assert_called_once()

            # assert result == schema


@pytest.mark.anyio
@pytest.mark.parametrize(
    "schema, schema_id",
    [
        (
            db.Schema(did="did123", name="schema1", version="1.0"),
            "did123:2:schema1:1.0",
        ),
        (None, "notindb"),
    ],
)
def test_delete_schema(db_session_mock: Session, schema, schema_id):
    db_session_mock.scalars.return_value.one_or_none.return_value = schema
    with patch("trustregistry.crud.select") as select_mock, patch(
        "trustregistry.crud.delete"
    ) as delete_mock:
        if schema:
            result = crud.delete_schema(db_session_mock, schema_id)

            select_mock.assert_called_once_with(db.Schema)
            select_mock(db.Schema).where.assert_called()

            delete_mock.assert_called_once_with(db.Schema)
            delete_mock(db.Schema).where.assert_called()

            db_session_mock.execute.assert_called_once()
            db_session_mock.commit.assert_called_once()

            assert result == schema
        else:
            with pytest.raises(SchemaDoesNotExistException):
                crud.delete_schema(db_session_mock, schema_id)
