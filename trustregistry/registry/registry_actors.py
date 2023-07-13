from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session

from shared.log_config import get_logger
from trustregistry import crud
from trustregistry.db import get_db
from shared.models.trustregistry import Actor

logger = get_logger(__name__)

router = APIRouter(prefix="/registry/actors", tags=["actor"])


@router.get("")
async def get_actors(db_session: Session = Depends(get_db)):
    logger.info("GET request received: Fetch all actors")
    db_actors = crud.get_actors(db_session)

    return {"actors": db_actors}


@router.post("")
async def register_actor(actor: Actor, db_session: Session = Depends(get_db)):
    bound_logger = logger.bind(body={"actor": actor})
    bound_logger.info("POST request received: Register actor")
    try:
        created_actor = crud.create_actor(db_session, actor=actor)
    except crud.ActorAlreadyExistsException as e:
        bound_logger.info("Bad request: Actor already exists.")
        raise HTTPException(status_code=409, detail=str(e)) from e

    return created_actor


@router.put("/{actor_id}")
async def update_actor(
    actor_id: str, actor: Actor, db_session: Session = Depends(get_db)
):
    bound_logger = logger.bind(body={"actor_id": actor_id, "actor": actor})
    bound_logger.info("PUT request received: Update actor")
    if actor.id and actor.id != actor_id:
        bound_logger.info("Bad request: Actor ID in request doesn't match ID in URL.")
        raise HTTPException(
            status_code=400,
            detail=f"The provided actor ID '{actor.id}' in the request body "
            f"does not match the actor ID '{actor_id}' in the URL.",
        )
    if not actor.id:
        actor.id = actor_id

    try:
        update_actor_result = crud.update_actor(db_session, actor=actor)
    except crud.ActorDoesNotExistException as e:
        bound_logger.info("Bad request: Actor not found.")
        raise HTTPException(
            status_code=404, detail=f"Actor with id {actor_id} not found."
        ) from e

    return update_actor_result


@router.get("/did/{actor_did}")
async def get_actor_by_did(actor_did: str, db_session: Session = Depends(get_db)):
    bound_logger = logger.bind(body={"actor_did": actor_did})
    bound_logger.info("GET request received: Get actor by DID")
    try:
        actor = crud.get_actor_by_did(db_session, actor_did=actor_did)
    except crud.ActorDoesNotExistException as e:
        bound_logger.info("Bad request: Actor not found.")
        raise HTTPException(
            status_code=404, detail=f"Actor with did {actor_did} not found."
        ) from e

    return actor


@router.get("/{actor_id}")
async def get_actor_by_id(actor_id: str, db_session: Session = Depends(get_db)):
    bound_logger = logger.bind(body={"actor_id": actor_id})
    bound_logger.info("GET request received: Get actor by ID")
    try:
        actor = crud.get_actor_by_id(db_session, actor_id=actor_id)
    except crud.ActorDoesNotExistException as e:
        bound_logger.info("Bad request: Actor not found.")
        raise HTTPException(
            status_code=404, detail=f"Actor with id {actor_id} not found."
        ) from e

    return actor


@router.delete("/{actor_id}", status_code=204)
async def remove_actor(actor_id: str, db_session: Session = Depends(get_db)):
    bound_logger = logger.bind(body={"actor_id": actor_id})
    bound_logger.info("DELETE request received: Delete actor by ID")
    try:
        crud.delete_actor(db_session, actor_id=actor_id)
    except crud.ActorDoesNotExistException:
        bound_logger.info("Bad request: Actor not found.")
        raise HTTPException(
            status_code=404, detail=f"Actor with id {actor_id} not found."
        )
