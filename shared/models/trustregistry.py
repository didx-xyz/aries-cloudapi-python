from typing import List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from shared.exceptions import CloudApiValueError

TrustRegistryRole = Literal["issuer", "verifier"]


class Actor(BaseModel):
    id: str
    name: str
    roles: List[TrustRegistryRole]
    did: str
    didcomm_invitation: Optional[str] = None
    image_url: Optional[str] = None

    @field_validator("did")
    @classmethod
    def did_validator(cls, did: str):
        if not did.startswith("did:"):
            raise CloudApiValueError("Only fully qualified DIDs allowed.")

        return did

    model_config = ConfigDict(validate_assignment=True, from_attributes=True)


def calc_schema_id(did: str, name: str, version: str) -> str:
    return f"{did}:2:{name}:{version}"


class Schema(BaseModel):
    did: str = Field(default=None)
    name: str = Field(default=None)
    version: str = Field(default=None)
    schema_id: str = Field(default=None, alias="id")

    @model_validator(mode="before")
    @classmethod
    def validate_and_set_values(cls, values: Union[dict, "Schema"]):
        if not isinstance(values, dict):
            values = values.__dict__

        try:
            for field in ["did", "name", "version"]:
                if ":" in values[field]:
                    raise CloudApiValueError(
                        f"Schema field `{field}` must not contain colon."
                    )
            did = values["did"]
            name = values["name"]
            version = values["version"]
        except KeyError:
            did = None
            name = None
            version = None

        schema_id = values.get("id")

        if schema_id is None:
            if None in (did, name, version):
                raise CloudApiValueError(
                    "Either `id` or all of (`did`, `name`, `version`) must be specified."
                )
            schema_id = calc_schema_id(did, name, version)
        else:
            if None not in (did, name, version):
                expected_id = calc_schema_id(did, name, version)
                if schema_id != expected_id:
                    raise CloudApiValueError(
                        f"Schema's `id` field does not match expected format: `{expected_id}`."
                    )
            else:
                # Extract did, name, and version from id if not specified
                try:
                    did, _, name, version = schema_id.split(":")
                except ValueError as exc:
                    raise CloudApiValueError(
                        "Invalid `id` field. It does not match the expected format."
                    ) from exc

        values["did"] = did
        values["name"] = name
        values["version"] = version
        values["id"] = schema_id
        return values

    model_config = ConfigDict(validate_assignment=True, from_attributes=True)
