from typing import Optional

from aries_cloudcontroller import ReceiveInvitationRequest
from pydantic import BaseModel


class CreateInvitation(BaseModel):
    alias: Optional[str] = None
    multi_use: Optional[bool] = None
    use_public_did: Optional[bool] = None


class AcceptInvitation(BaseModel):
    alias: Optional[str] = None
    invitation: ReceiveInvitationRequest
