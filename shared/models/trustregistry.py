from typing import List, Optional

from pydantic import BaseModel, Field, root_validator
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
            raise ValueError("Only fully qualified DIDs allowed.")

        return did

    class Config:
        validate_assignment = True
        orm_mode = True


def calc_schema_id(did: str, name: str, version: str) -> str:
    return f"{did}:2:{name}:{version}"


class Schema(BaseModel):
    did: str = Field(default=None)
    name: str = Field(default=None)
    version: str = Field(default=None)
    id: str = Field(default=None)

    # pylint: disable=no-self-argument
    @root_validator
    def validate_and_set_values(cls, values):
        for v in ["did", "name", "version"]:
            if ":" in values.get(v, ""):
                raise ValueError(f"Schema field `{v}` must not contain colon.")

        did = values.get("did")
        name = values.get("name")
        version = values.get("version")
        id = values.get("id")

        if id is None:
            if None in (did, name, version):
                raise ValueError(
                    "Either `id` or all of (`did`, `name`, `version`) must be specified."
                )
            id = calc_schema_id(did, name, version)
        else:
            if None not in (did, name, version):
                expected_id = calc_schema_id(did, name, version)
                if id != expected_id:
                    raise ValueError(
                        f"Schema's `id` field does not match expected format: `{expected_id}`."
                    )
            else:
                # Extract did, name, and version from id if not specified
                try:
                    did, _, name, version = id.split(":")
                except ValueError:
                    raise ValueError(
                        "Invalid `id` field. It does not match the expected format."
                    )

        values["did"] = did
        values["name"] = name
        values["version"] = version
        values["id"] = id
        return values

    class Config:
        validate_assignment = True
        orm_mode = True
