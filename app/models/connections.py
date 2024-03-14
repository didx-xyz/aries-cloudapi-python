from typing import Literal, Optional

from aries_cloudcontroller import ReceiveInvitationRequest
from pydantic import BaseModel


class CreateInvitation(BaseModel):
    alias: Optional[str] = None
    multi_use: Optional[bool] = None
    use_public_did: Optional[bool] = None


class AcceptInvitation(BaseModel):
    alias: Optional[str] = None
    invitation: ReceiveInvitationRequest


State = Literal[
    "active",
    "response",
    "request",
    "start",
    "completed",
    "init",
    "error",
    "invitation",
    "abandoned",
]

Role = Literal["invitee", "requester", "inviter", "responder"]

Protocol = Literal["connections/1.0", "didexchange/1.0"]
