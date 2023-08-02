from typing import List, Optional

from aries_cloudcontroller import InvitationMessage
from aries_cloudcontroller.model.attachment_def import AttachmentDef
from pydantic import BaseModel


class ConnectToPublicDid(BaseModel):
    public_did: str


class CreateOobInvitation(BaseModel):
    alias: Optional[str] = None
    multi_use: Optional[bool] = None
    use_public_did: Optional[bool] = None
    attachments: Optional[List[AttachmentDef]] = None
    handshake_protocols: Optional[List[str]] = None
    create_connection: Optional[bool] = None


class AcceptOobInvitation(BaseModel):
    alias: Optional[str] = None
    use_existing_connection: Optional[bool] = None
    invitation: InvitationMessage
