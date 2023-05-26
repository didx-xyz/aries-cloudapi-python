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
    id: str

    @root_validator(pre=True)
    def default_id_create(cls, values):
        for v in ["did", "name", "version"]:
            if ":" in values[v]:
                raise ValueError(f"Schema field `{v}` must not contain colon.")
        expected_id = f"{values['did']}:2:{values['name']}:{values['version']}"
        if values.get("id") != expected_id:
            raise ValueError(
                f"Schema's `id` field does not match expected format: {expected_id}"
            )
        return values

    class Config:
        validate_assignment = True
        orm_mode = True
