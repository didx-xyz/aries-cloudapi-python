from typing import Optional

from aries_cloudcontroller import ReceiveInvitationRequest
from pydantic import BaseModel


class CreateInvitation(BaseModel):
    alias: Optional[str] = None
    multi_use: bool = False
    use_public_did: bool = False


class AcceptInvitation(BaseModel):
    alias: Optional[str] = None
    invitation: ReceiveInvitationRequest
