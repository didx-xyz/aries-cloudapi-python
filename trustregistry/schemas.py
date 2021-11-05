from typing import List, Optional

from pydantic import BaseModel, root_validator
from pydantic.class_validators import validator


class Actor(BaseModel):
    id: str
    name: str
    roles: List[str]
    did: str
    didcomm_invitation: Optional[str] = None

    @validator("did")
    @classmethod
    def did_validator(cls, did: str):
        if not did.startswith("did:"):
            raise ValueError("Only fully qualified DIDs allowed")

        return did

    class Config:
        validate_assignment = True
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
