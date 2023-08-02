from pydantic import BaseModel


class Message(BaseModel):
    connection_id: str
    content: str


class TrustPingMsg(BaseModel):
    connection_id: str
    comment: str
