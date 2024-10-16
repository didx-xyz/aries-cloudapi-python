from typing import List

from pydantic import BaseModel, Field


class CreateCredentialDefinition(BaseModel):
    schema_id: str = Field(..., examples=["CXQseFxV34pcb8vf32XhEa:2:test_schema:0.3"])
    tag: str = Field(..., examples=["default"])
    support_revocation: bool = Field(default=False)


class CredentialDefinition(BaseModel):
    id: str = Field(..., examples=["5Q1Zz9foMeAA8Q7mrmzCfZ:3:CL:7:default"])
    tag: str = Field(..., examples=["default"])
    schema_id: str = Field(..., examples=["CXQseFxV34pcb8vf32XhEa:2:test_schema:0.3"])


class CreateSchema(BaseModel):
    name: str = Field(..., examples=["test_schema"])
    version: str = Field(..., examples=["0.3.0"])
    attribute_names: List[str] = Field(..., examples=[["name", "age"]])


class CredentialSchema(BaseModel):
    id: str = Field(..., examples=["CXQseFxV34pcb8vf32XhEa:2:test_schema:0.3"])
    name: str = Field(..., examples=["test_schema"])
    version: str = Field(..., examples=["0.3.0"])
    attribute_names: List[str] = Field(..., examples=[["name", "age"]])
