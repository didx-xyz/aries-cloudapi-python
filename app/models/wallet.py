from pydantic import BaseModel, Field


class SetDidEndpointRequest(BaseModel):
    endpoint: str = Field(...)
