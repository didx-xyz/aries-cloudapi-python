from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session

import crud
from db import get_db
from schemas import Actor

router = APIRouter(prefix="/registry/actors", tags=["actor"])


@router.get("/")
async def get_actors(db: Session = Depends(get_db)):
    db_actors = crud.get_actors(db)
    return {"actors": db_actors}


@router.post("/")
async def register_actor(actor: Actor, db: Session = Depends(get_db)):
    created_actor = crud.create_actor(db, actor=actor)
    return created_actor


@router.post("/{actor_id}")
async def update_actor(actor_id: str, actor: Actor, db: Session = Depends(get_db)):
    update_actor_result = crud.update_actor(db, actor=actor, actor_id=actor_id)
    if update_actor_result is None:
        raise HTTPException(status_code=404, detail="Actor not found.")
    return update_actor_result


@router.delete("/{actor_id}")
async def remove_actor(actor_id: str, db: Session = Depends(get_db)):
    delete_actor_result = crud.delete_actor(db, actor_id=actor_id)
    if delete_actor_result is None:
        raise HTTPException(status_code=404, detail="Actor not found.")
