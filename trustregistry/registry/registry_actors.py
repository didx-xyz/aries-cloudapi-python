from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session

from trustregistry import crud
from trustregistry.db import get_db
from trustregistry.schemas import Actor

router = APIRouter(prefix="/registry/actors", tags=["actor"])


@router.get("")
async def get_actors(db: Session = Depends(get_db)):
    db_actors = crud.get_actors(db)
    return {"actors": db_actors}


@router.post("")
async def register_actor(actor: Actor, db: Session = Depends(get_db)):
    try:
        created_actor = crud.create_actor(db, actor=actor)
    except crud.ActorAlreadyExistsException:
        raise HTTPException(status_code=405, detail="Actor already exists.")
    return created_actor


@router.post("/{actor_id}")
async def update_actor(actor_id: str, actor: Actor, db: Session = Depends(get_db)):
    try:
        update_actor_result = crud.update_actor(db, actor=actor)
    except crud.ActorDoesNotExistException:
        raise HTTPException(status_code=404, detail="Actor not found.")
    return update_actor_result


@router.get("/did/{actor_did}")
async def get_actor_by_did(actor_did: str, db: Session = Depends(get_db)):
    try:
        actor = crud.get_actor_by_did(db, actor_did=actor_did)
    except crud.ActorDoesNotExistException:
        raise HTTPException(status_code=404, detail="Actor not found.")
    return actor


@router.get("/{actor_id}")
async def get_actor_by_id(actor_id: str, db: Session = Depends(get_db)):
    try:
        actor = crud.get_actor_by_id(db, actor_id=actor_id)
    except crud.ActorDoesNotExistException:
        raise HTTPException(status_code=404, detail="Actor not found.")
    return actor


@router.delete("/{actor_id}", status_code=204)
async def remove_actor(actor_id: str, db: Session = Depends(get_db)):
    try:
        crud.delete_actor(db, actor_id=actor_id)
    except crud.ActorDoesNotExistException:
        raise HTTPException(status_code=404, detail="Actor not found.")
