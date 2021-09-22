import logging
from fastapi import APIRouter
from pydantic import BaseModel, validator
from typing import List
from slugify import Slugify

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/registry/actor", tags=["actor"])

custom_slugify = Slugify(to_lower=True, separator="_")


class ActorID(BaseModel):
    id: str


class ActorUpdateFields(BaseModel):
    name: str
    slug: str = None
    roles: List[str] = ["issuer", "verifier"]
    didcomm_invitation: str = None
    did: str = None

    @validator("slug", always=True)
    def slugify_id_for_name(cls, value, values):
        return custom_slugify(values["name"])


class RegisterActor(ActorUpdateFields, ActorID):
    pass


@router.post("")
async def register_actor(actor: RegisterActor):
    return actor.dict()


@router.put("/{actor_id}")
async def update_actor(actor_id: str, actor: ActorUpdateFields):
    return actor.dict()


@router.delete("/{actor_id}")
async def remove_actor(actor_id: str):
    return actor_id
