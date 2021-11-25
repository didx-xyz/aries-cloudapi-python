from typing import Literal, Optional

from aries_cloudcontroller import ConnRecord
from pydantic import BaseModel


class Connection(BaseModel):
    connection_id: str
    connection_protocol: Literal["connections/1.0", "didexchange/1.0"]
    created_at: str
    invitation_mode: Literal["once", "multi", "static"]
    their_role: Literal["invitee", "requester", "inviter", "responder"]
    state: str  # did-exchange state

    my_did: Optional[str]
    alias: Optional[str] = None
    their_did: Optional[str] = None
    their_label: Optional[str] = None
    their_public_did: Optional[str] = None
    updated_at: Optional[str] = None
    error_msg: Optional[str] = None
    invitation_key: Optional[str] = None
    invitation_msg_id: Optional[str] = None


def conn_record_to_connection(connection_record: ConnRecord):
    return Connection(
        connection_id=connection_record.connection_id,
        connection_protocol=connection_record.connection_protocol,
        created_at=connection_record.created_at,
        invitation_mode=connection_record.invitation_mode,
        their_role=connection_record.their_role,
        my_did=connection_record.my_did,
        state=connection_record.rfc23_state,
        alias=connection_record.alias,
        their_did=connection_record.their_did,
        their_label=connection_record.their_label,
        their_public_did=connection_record.their_public_did,
        updated_at=connection_record.updated_at,
        error_msg=connection_record.error_msg,
        invitation_key=connection_record.invitation_key,
        invitation_msg_id=connection_record.invitation_msg_id,
    )
