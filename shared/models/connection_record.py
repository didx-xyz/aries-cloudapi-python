from typing import Literal, Optional

from aries_cloudcontroller import ConnRecord
from pydantic import BaseModel


class Connection(BaseModel):
    # accept: Optional[str] = None
    alias: Optional[str] = None
    connection_id: Optional[str] = None
    connection_protocol: Optional[Literal["connections/1.0", "didexchange/1.0"]] = None
    created_at: Optional[str] = None
    error_msg: Optional[str] = None
    # inbound_connection_id
    invitation_key: Optional[str] = None
    invitation_mode: Optional[Literal["once", "multi", "static"]] = None
    invitation_msg_id: Optional[str] = None
    my_did: Optional[str] = None
    # request_id: Optional[str] = None
    # rfc23_state: Optional[str] = None
    state: Optional[str] = None
    their_did: Optional[str] = None
    their_label: Optional[str] = None
    their_public_did: Optional[str] = None
    their_role: Optional[Literal["invitee", "requester", "inviter", "responder"]] = None
    updated_at: Optional[str] = None


def conn_record_to_connection(connection_record: ConnRecord):
    return Connection(
        alias=connection_record.alias,
        connection_id=connection_record.connection_id,
        connection_protocol=connection_record.connection_protocol,
        created_at=connection_record.created_at,
        error_msg=connection_record.error_msg,
        invitation_key=connection_record.invitation_key,
        invitation_mode=connection_record.invitation_mode,
        invitation_msg_id=connection_record.invitation_msg_id,
        my_did=connection_record.my_did,
        state=connection_record.rfc23_state,
        their_did=connection_record.their_did,
        their_label=connection_record.their_label,
        their_public_did=connection_record.their_public_did,
        their_role=connection_record.their_role,
        updated_at=connection_record.updated_at,
    )
