from typing import List

from trustregistry import crud
from trustregistry import schemas
from trustregistry.tests.test_main import override_get_db

# from trustregistry.schemas import Actor

actor_model = schemas.Actor(
    id="mickey-mouse",
    name="Mickey Mouse",
    roles="verifier, issuer",
    didcomm_invitation="xyz",
    did="abc",
)

actor_model_update = schemas.Actor(
    id="mickey-mouse-2",
    name="Mickey Mouse 2",
    roles="verifier, issuer",
    didcomm_invitation="xyz",
    did="abc",
)


def test_get_actors():

    for db in override_get_db():
        actors = crud.get_actors(db)
        assert isinstance(actors, List)


def test_create_actor():
    for db in override_get_db():
        actor = crud.create_actor(db, actor=actor_model)
        actor = actor.__dict__
        del actor["_sa_instance_state"]
        assert actor == actor_model.dict()

        actor_retry = crud.create_actor(db, actor=actor_model)
        assert actor_retry is None


def test_update_actor():
    for db in override_get_db():
        updated_actor = crud.update_actor(
            db, actor=actor_model_update, actor_id=actor_model.id
        )
        updated_actor = updated_actor.__dict__
        del updated_actor["_sa_instance_state"]
        assert updated_actor == actor_model_update.dict()

        updated_actor_non_ex = crud.update_actor(
            db, actor=actor_model_update, actor_id="idontexist"
        )
        assert updated_actor_non_ex is None


def test_delete_actor():
    for db in override_get_db():
        deleted_actor = crud.delete_actor(db, actor_id=actor_model_update.id)
        deleted_actor = deleted_actor.__dict__
        del deleted_actor["_sa_instance_state"]
        assert deleted_actor == actor_model_update.dict()

        delete_non_ex_actor = crud.delete_actor(db, actor_id="idontexist")
        assert delete_non_ex_actor is None


def test_get_schemas():
    for db in override_get_db():
        schemas_db = crud.get_schemas(db)
        assert isinstance(schemas_db, List)


new_schema = schemas.Schema(did="abc", name="awesomeschema", version="0.4.20")

update_schema = schemas.Schema(did="abcde", name="awesomeschema", version="0.4.20")


def test_create_schema():
    for db in override_get_db():
        schema_created = crud.create_schema(db, schema=new_schema)
        schema_created = schema_created.__dict__
        del schema_created["_sa_instance_state"]
        assert schema_created == new_schema.dict()

        schema_updated_non_ex = crud.create_schema(db, schema=new_schema)
        assert schema_updated_non_ex == 1


def test_update_schema():
    for db in override_get_db():
        schema_updated = crud.update_schema(
            db, schema=update_schema, schema_did=new_schema.did
        )
        schema_updated = schema_updated.__dict__
        del schema_updated["_sa_instance_state"]
        assert schema_updated == update_schema.dict()

        schema_updated_non_ex = crud.update_schema(
            db, schema=update_schema, schema_did="idontexist"
        )
        assert schema_updated_non_ex is None


def test_delete_schema():
    for db in override_get_db():
        schema_deleted = crud.delete_schema(db, schema_did=update_schema.did)
        schema_deleted = schema_deleted.__dict__
        del schema_deleted["_sa_instance_state"]
        assert schema_deleted == update_schema.dict()

        schema_deleted_non_ex = crud.delete_schema(db, schema_did=update_schema.did)
        assert schema_deleted_non_ex is None
