from typing import List, Optional

from pydantic import BaseModel


class Actor(BaseModel):
    id: str
    name: str
    roles: List[str]
    did: str
    didcomm_invitation: Optional[str] = None

    class Config:
        orm_mode = True


class Schema(BaseModel):
    did: str
    name: str
    version: str
    id: str = None

    class Config:
        orm_mode = True
