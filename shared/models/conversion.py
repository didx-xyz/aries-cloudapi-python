from typing import Dict, Optional, Tuple, Union

from aries_cloudcontroller import (
    ConnRecord,
    IndyProof,
    IndyProofRequest,
    V10CredentialExchange,
    V10PresentationExchange,
    V20CredExRecord,
    V20PresExRecord,
)

from shared.models.protocol import (
    IssueCredentialProtocolVersion,
    PresentProofProtocolVersion,
)
from shared.models.topics import Connection, CredentialExchange, PresentationExchange


def string_to_bool(verified: Optional[str]) -> Optional[bool]:
    if verified == "true":
        return True
    elif verified == "false":
        return False
    else:
        return None


def v1_presentation_state_to_rfc_state(state: Optional[str]) -> Optional[str]:
    translation_dict = {
        "abandoned": "abandoned",
        "done": "done",
        "presentation_acked": "done",
        "presentation_received": "presentation-received",
        "presentation_sent": "presentation-sent",
        "proposal_received": "proposal-received",
        "proposal_sent": "proposal-sent",
        "request_received": "request-received",
        "request_sent": "request-sent",
        "verified": "done",
    }

    if not state or state not in translation_dict:
        return None

    return translation_dict[state]


def presentation_record_to_model(
    record: Union[V20PresExRecord, V10PresentationExchange]
) -> PresentationExchange:
    if isinstance(record, V20PresExRecord):
        try:
            presentation = (
                IndyProof(**record.by_format.pres["indy"])
                if record.by_format.pres
                else None
            )
        except AttributeError:
            presentation = None

        try:
            presentation_request = IndyProofRequest(
                **record.by_format.pres_request["indy"]
            )
        except AttributeError:
            presentation_request = None

        return PresentationExchange(
            connection_id=record.connection_id,
            created_at=record.created_at,
            error_msg=record.error_msg,
            parent_thread_id=record.pres_request.id if record.pres_request else None,
            presentation=presentation,
            presentation_request=presentation_request,
            proof_id="v2-" + str(record.pres_ex_id),
            protocol_version=PresentProofProtocolVersion.v2.value,
            role=record.role,
            state=record.state,
            thread_id=record.thread_id,
            updated_at=record.updated_at,
            verified=string_to_bool(record.verified),
        )
    elif isinstance(record, V10PresentationExchange):
        return PresentationExchange(
            connection_id=record.connection_id,
            created_at=record.created_at,
            error_msg=record.error_msg,
            parent_thread_id=record.presentation_request_dict.id
            if record.presentation_request_dict
            else None,
            presentation=record.presentation,
            presentation_request=record.presentation_request,
            proof_id="v1-" + str(record.presentation_exchange_id),
            protocol_version=PresentProofProtocolVersion.v1.value,
            role=record.role,
            state=v1_presentation_state_to_rfc_state(record.state),
            thread_id=record.thread_id,
            updated_at=record.updated_at,
            verified=string_to_bool(record.verified),
        )
    else:
        raise ValueError("Record format unknown.")


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


def credential_record_to_model_v1(record: V10CredentialExchange) -> CredentialExchange:
    attributes = attributes_from_record_v1(record)

    return CredentialExchange(
        attributes=attributes,
        connection_id=record.connection_id,
        created_at=record.created_at,
        credential_definition_id=record.credential_definition_id,
        credential_id=f"v1-{record.credential_exchange_id}",
        error_msg=record.error_msg,
        protocol_version=IssueCredentialProtocolVersion.v1,
        role=record.role,
        schema_id=record.schema_id,
        state=v1_credential_state_to_rfc_state(record.state),
        thread_id=record.thread_id,
        updated_at=record.updated_at,
        type="indy"
    )


def attributes_from_record_v1(
    record: V10CredentialExchange,
) -> Optional[Dict[str, str]]:
    preview = None

    if (
        record.credential_proposal_dict
        and record.credential_proposal_dict.credential_proposal
    ):
        preview = record.credential_proposal_dict.credential_proposal

    return {attr.name: attr.value for attr in preview.attributes} if preview else None


def v1_credential_state_to_rfc_state(state: Optional[str]) -> Optional[str]:
    translation_dict = {
        "abandoned": "abandoned",
        "credential_acked": "done",
        "credential_issued": "credential-issued",
        "credential_received": "credential-received",
        "done": "done",
        "offer_received": "offer-received",
        "offer_sent": "offer-sent",
        "proposal_received": "proposal-received",
        "proposal_sent": "proposal-sent",
        "request_received": "request-received",
        "request_sent": "request-sent",
    }

    if not state or state not in translation_dict:
        return None

    return translation_dict[state]


def credential_record_to_model_v2(record: V20CredExRecord) -> CredentialExchange:
    attributes = attributes_from_record_v2(record)
    schema_id, credential_definition_id = schema_cred_def_from_record(record)

    return CredentialExchange(
        attributes=attributes,
        connection_id=record.connection_id,
        created_at=record.created_at,
        credential_definition_id=credential_definition_id,
        credential_id=f"v2-{record.cred_ex_id}",
        error_msg=record.error_msg,
        protocol_version=IssueCredentialProtocolVersion.v2,
        role=record.role,
        schema_id=schema_id,
        state=record.state,
        thread_id=record.thread_id,
        updated_at=record.updated_at,
    )


def schema_cred_def_from_record(
    record: V20CredExRecord,
) -> Tuple[Optional[str], Optional[str]]:
    if record.by_format and record.by_format.cred_offer:
        indy = record.by_format.cred_offer.get("indy", {})
    elif record.by_format and record.by_format.cred_proposal:
        indy = record.by_format.cred_proposal.get("indy", {})
    else:
        indy = {}

    schema_id = indy.get("schema_id", None)
    credential_definition_id = indy.get("cred_def_id", None)

    return schema_id, credential_definition_id


def attributes_from_record_v2(record: V20CredExRecord) -> Optional[Dict[str, str]]:
    preview = None

    if record.cred_preview:
        preview = record.cred_preview
    elif record.cred_offer and record.cred_offer.credential_preview:
        preview = record.cred_offer.credential_preview
    elif record.cred_proposal and record.cred_proposal.credential_preview:
        preview = record.cred_proposal.credential_preview

    return {attr.name: attr.value for attr in preview.attributes} if preview else None
