from pydantic import BaseModel, root_validator


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
    id: str = None

    @root_validator
    def default_id_create(cls, values):
        values["id"] = f"{values['did']}:{values['name']}:{values['version']}"
        return values

    class Config:
        validate_assignment = True
        orm_mode = True
