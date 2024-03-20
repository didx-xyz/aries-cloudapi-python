from typing import List, Optional

from aries_cloudcontroller import AttachmentDef, InvitationMessage
from pydantic import BaseModel, model_validator

from shared.exceptions.cloudapi_value_error import CloudApiValueError


class ConnectToPublicDid(BaseModel):
    public_did: str


class CreateOobInvitation(BaseModel):
    alias: Optional[str] = None
    multi_use: Optional[bool] = None
    use_public_did: Optional[bool] = None
    attachments: Optional[List[AttachmentDef]] = None
    handshake_protocols: Optional[List[str]] = None
    create_connection: Optional[bool] = None

    @model_validator(mode="before")
    @classmethod
    def validate_one_of_create_connection_or_attachments(cls, values):
        create, attachments = values.get("create_connection"), values.get("attachments")
        if not create and not attachments:
            raise CloudApiValueError(
                "One or both of 'create_connection' and 'attachments' must be included."
            )
        return values


class AcceptOobInvitation(BaseModel):
    alias: Optional[str] = None
    use_existing_connection: Optional[bool] = None
    invitation: InvitationMessage
