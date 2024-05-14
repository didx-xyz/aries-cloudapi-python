from typing import Dict, Literal, Optional, Tuple

from aries_cloudcontroller import V10CredentialExchange, V20CredExRecord
from pydantic import BaseModel, Field

from shared.models.protocol import IssueCredentialProtocolVersion

State = Literal[
    "proposal-sent",
    "proposal-received",
    "offer-sent",
    "offer-received",
    "request-sent",
    "request-received",
    "credential-issued",
    "credential-received",
    "credential-revoked",
    "abandoned",
    "done",
    "deleted",
]

Role = Literal["issuer", "holder"]


class CredentialExchange(BaseModel):
    # unused fields:
    # auto_offer: Optional[str] = None
    # auto_remove: Optional[str] = None
    # initiator: Optional[str] = None
    # credential_exchange_id stored as credential_id instead

    # Attributes can be None in proposed state
    attributes: Optional[Dict[str, str]] = None
    # Connection id can be None in connectionless exchanges
    connection_id: Optional[str] = None
    created_at: str
    credential_definition_id: Optional[str] = None
    credential_id: str = Field(..., deprecated=True)
    credential_exchange_id: str = Field(...)
    did: Optional[str] = None
    error_msg: Optional[str] = None
    protocol_version: IssueCredentialProtocolVersion
    role: Role
    schema_id: Optional[str] = None
    # state can be None in proposed state
    state: Optional[State] = None
    # Thread id can be None in connectionless exchanges
    thread_id: Optional[str] = None
    type: str = "indy"
    updated_at: str


def credential_record_to_model_v1(record: V10CredentialExchange) -> CredentialExchange:
    attributes = attributes_from_record_v1(record)
    credential_exchange_id = f"v1-{record.credential_exchange_id}"

    return CredentialExchange(
        attributes=attributes,
        connection_id=record.connection_id,
        created_at=record.created_at,
        credential_definition_id=record.credential_definition_id,
        credential_id=credential_exchange_id,
        credential_exchange_id=credential_exchange_id,
        error_msg=record.error_msg,
        protocol_version=IssueCredentialProtocolVersion.v1,
        role=record.role,
        schema_id=record.schema_id,
        state=v1_credential_state_to_rfc_state(record.state),
        thread_id=record.thread_id,
        updated_at=record.updated_at,
        type="indy",
    )


def v1_credential_state_to_rfc_state(state: Optional[str]) -> Optional[str]:
    translation_dict = {
        "abandoned": "abandoned",
        "credential_acked": "done",
        "credential_issued": "credential-issued",
        "credential_received": "credential-received",
        "credential_revoked": "credential-revoked",
        "deleted": "deleted",
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


def back_to_v1_credential_state(state: Optional[str]) -> Optional[str]:
    translation_dict = {
        "abandoned": "abandoned",
        "deleted": "deleted",
        "done": "credential_acked",
        "credential-issued": "credential_issued",
        "credential-received": "credential_received",
        "credential-revoked": "credential_revoked",
        "offer-received": "offer_received",
        "offer-sent": "offer_sent",
        "proposal-received": "proposal_received",
        "proposal-sent": "proposal_sent",
        "request-received": "request_received",
        "request-sent": "request_sent",
    }

    return translation_dict[state]


def credential_record_to_model_v2(record: V20CredExRecord) -> CredentialExchange:
    attributes = attributes_from_record_v2(record)
    schema_id, credential_definition_id = schema_cred_def_from_record(record)
    credential_exchange_id = f"v2-{record.cred_ex_id}"

    return CredentialExchange(
        attributes=attributes,
        connection_id=record.connection_id,
        created_at=record.created_at,
        credential_definition_id=credential_definition_id,
        credential_id=credential_exchange_id,
        credential_exchange_id=credential_exchange_id,
        did=(
            record.by_format.cred_offer["ld_proof"]["credential"]["issuer"]
            if record.by_format and "ld_proof" in record.by_format.cred_offer
            else None
        ),
        error_msg=record.error_msg,
        protocol_version=IssueCredentialProtocolVersion.v2,
        role=record.role,
        schema_id=schema_id,
        state=record.state,
        thread_id=record.thread_id,
        updated_at=record.updated_at,
        type=(
            list(record.by_format.cred_offer.keys())[0] if record.by_format else "indy"
        ),
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


def attributes_from_record_v2(record: V20CredExRecord) -> Optional[Dict[str, str]]:
    preview = None

    if record.cred_preview:
        preview = record.cred_preview
    elif record.cred_offer and record.cred_offer.credential_preview:
        preview = record.cred_offer.credential_preview
    elif record.cred_proposal and record.cred_proposal.credential_preview:
        preview = record.cred_proposal.credential_preview

    return {attr.name: attr.value for attr in preview.attributes} if preview else None
