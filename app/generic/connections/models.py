from aries_cloudcontroller import ConnRecord

from shared_models import Connection


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
