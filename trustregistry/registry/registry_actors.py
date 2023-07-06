from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session

from trustregistry import crud
from trustregistry.config.log_config import get_logger
from trustregistry.db import get_db
from trustregistry.schemas import Actor

logger = get_logger(__name__)

router = APIRouter(prefix="/registry/actors", tags=["actor"])


@router.get("")
async def get_actors(db: Session = Depends(get_db)):
    logger.info("GET request received: Fetch all actors")
    db_actors = crud.get_actors(db)

    return {"actors": db_actors}


@router.post("")
async def register_actor(actor: Actor, db: Session = Depends(get_db)) -> Actor:
    logger.info("POST request received: Register actor")
    try:
        created_actor = crud.create_actor(db, actor=actor)
    except crud.ActorAlreadyExistsException:
        raise HTTPException(status_code=405, detail="Actor already exists.")

    return created_actor


@router.put("/{actor_id}")
async def update_actor(actor_id: str, actor: Actor, db: Session = Depends(get_db)) -> Actor:
    logger.info("PUT request received: Update actor")
    if actor.id and actor.id != actor_id:
        raise HTTPException(
            status_code=400,
            detail=f"The provided actor ID '{actor.id}' in the request body "
            f"does not match the actor ID '{actor_id}' in the URL.",
        )
    if not actor.id:
        actor.id = actor_id

    try:
        update_actor_result = crud.update_actor(db, actor=actor)
    except crud.ActorDoesNotExistException:
        raise HTTPException(status_code=404, detail="Actor not found.")

    return update_actor_result


@router.get("/did/{actor_did}")
async def get_actor_by_did(actor_did: str, db: Session = Depends(get_db)) -> Actor:
    logger.info("GET request received: Get actor by DID")
    try:
        actor = crud.get_actor_by_did(db, actor_did=actor_did)
    except crud.ActorDoesNotExistException:
        raise HTTPException(status_code=404, detail="Actor not found.")

    return actor

@router.get("/{actor_name}")
async def get_actor_by_name(actor_name: str, db: Session = Depends(get_db)) -> Actor:
    actor = crud.get_actor_by_name(db, actor_name=actor_name)
    if actor is None:
        raise HTTPException(status_code=404, detail="Actor not found.")
    return actor

@router.get("/{actor_id}")
async def get_actor_by_id(actor_id: str, db: Session = Depends(get_db)) -> Actor:
    logger.info("GET request received: Get actor by ID")
    try:
        actor = crud.get_actor_by_id(db, actor_id=actor_id)
    except crud.ActorDoesNotExistException:
        raise HTTPException(status_code=404, detail="Actor not found.")

    return actor


@router.delete("/{actor_id}", status_code=204)
async def remove_actor(actor_id: str, db: Session = Depends(get_db)) -> None:
    logger.info("DELETE request received: Delete actor by ID")
    try:
        crud.delete_actor(db, actor_id=actor_id)
    except crud.ActorDoesNotExistException:
        raise HTTPException(status_code=404, detail="Actor not found.")
