from pydantic import BaseModel


class Actor(BaseModel):
    id: str
    name: str
    roles: str
    didcomm_invitation: str = None
    did: str = None

    class Config:
        orm_mode = True


class Schema(BaseModel):
    did: str
    name: str
    version: str

    class Config:
        orm_mode = True
