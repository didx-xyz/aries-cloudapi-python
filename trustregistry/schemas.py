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

    @root_validator(pre=True)
    def default_id_create(cls, values):
        for v in ["name", "version"]:
            if ":" in values[v]:
                raise ValueError(f"{v} must not contain colon.")
        values["id"] = f"{values['did']}:{values['name']}:{values['version']}"
        if values["did"].endswith(tuple([f":{n}" for n in range(1, 4)])):
            values["did"] = values["did"][:-2]
        return values

    class Config:
        validate_assignment = True
        orm_mode = True
