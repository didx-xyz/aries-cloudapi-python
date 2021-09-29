import json
import os

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from pydantic import BaseModel
from typing import List

from dependencies import read_registry

ENV = os.getenv("ENV", "test")
if ENV == "prod":
    REGISTRY_FILE_PATH = os.getenv("REGISTRYFILE", "./registryfiles/trustregistry.json")
else:
    REGISTRY_FILE_PATH = "./registryfiles/trustregistry_test.json"

router = APIRouter(prefix="/registry/actors", tags=["actor"])


class Actor(BaseModel):
    id: str
    name: str
    roles: List[str] = ["issuer", "verifier"]
    didcomm_invitation: str = None
    did: str = None


def _actor_exists(actor_id: str, actors: list):
    actor_names = [actor["id"] for actor in actors]
    return actor_id in actor_names


@router.get("/")
async def get_actors(register=Depends(read_registry)):
    return register["actors"]


@router.post("/")
async def register_actor(new_actor: Actor, register=Depends(read_registry)):
    if _actor_exists(new_actor.id, register["actors"]):
        raise HTTPException(status_code=405, detail="Actor alrady exists.")
    with open(REGISTRY_FILE_PATH, "w") as tr:
        register["actors"].append(new_actor.dict())
        json.dump(register, tr, ensure_ascii=False, indent=4)
    return {}


@router.post("/{actor_id}")
async def update_actor(
    actor_id: str, new_actor: Actor, register=Depends(read_registry)
):
    if not _actor_exists(actor_id, register["actors"]):
        raise HTTPException(status_code=404, detail="Actor not found.")
    with open(REGISTRY_FILE_PATH, "w") as tr:
        for actor in register["actors"]:
            if actor["id"] == actor_id:
                actor = new_actor.dict()
        json.dump(register, tr, ensure_ascii=False, indent=4)
    return {}


@router.delete("/{actor_id}")
async def remove_actor(actor_id: str, register=Depends(read_registry)):
    if not _actor_exists(actor_id, register["actors"]):
        raise HTTPException(status_code=404, detail="Actor not found.")
    with open(REGISTRY_FILE_PATH, "w") as tr:
        for i, actor in enumerate(register["actors"]):
            if actor["id"] == actor_id:
                del register["actors"][i]
        json.dump(register, tr, ensure_ascii=False, indent=4)
    return {}
