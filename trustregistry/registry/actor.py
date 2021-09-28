import json

from trustregistry.main import registry
from fastapi import APIRouter
from pydantic import BaseModel, validator
from typing import List
from slugify import Slugify

router = APIRouter(prefix="/registry/actor", tags=["actor"])

custom_slugify = Slugify(to_lower=True, separator="_")


class ActorID(BaseModel):
    id: str


class ActorUpdateFields(BaseModel):
    name: str
    roles: List[str] = ["issuer", "verifier"]
    didcomm_invitation: str = None
    did: str = None


class RegisterActor(ActorUpdateFields, ActorID):
    pass


@router.post("/")
async def register_actor(new_actor: RegisterActor):
    with open("./registryfiles/trustregistry.json", "r+") as tr:
        registry_file = json.load(tr)
        # We could check whether the actor (id) is already present and return an error
        # This way this endpoint is an "update" in disguise - agreed it's fine for now though
        registry_file["actors"].append(new_actor.dict())
        tr.write(json.dumps(registry_file))
    return {}


@router.put("/{actor_id}")
async def update_actor(actor_id: str, new_actor: ActorUpdateFields):
    with open("./registryfiles/trustregistry.json", "r+") as tr:
        registry_file = json.load(tr)
        for actor in registry_file["actors"]:
            if actor["id"] == actor_id:
                actor = new_actor.dict()
        tr.write(json.dumps(registry_file))
    return {}


@router.delete("/{actor_id}")
async def remove_actor(actor_id: str):
    with open("./registryfiles/trustregistry.json", "r+") as tr:
        registry_file = json.load(tr)
        for i, actor in enumerate(registry_file["actors"]):
            if actor["id"] == actor_id:
                del registry_file["actors"][i]
        tr.write(json.dumps(registry_file))
    return {}
