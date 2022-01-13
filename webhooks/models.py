from typing import Any, Optional
from enum import Enum
from typing_extensions import Literal
from pydantic import BaseModel


class ConnectionsHook(BaseModel):
    accept: Literal["manual", "auto"]
    connection_id: str
    connection_protocol: Literal["connections/1.0", "didexchange/1.0"]
    created_at: str
    invitation_key: Optional[str]
    invitation_mode: Literal["once", "multi", "static"]
    invitation_msg_id: Optional[str] = None
    my_did: Optional[str]
    request_id: Optional[str]
    rfc23_state: Literal[
        "start",
        "invitation-received",
        "request-sent",
        "response-received",
        "abandoned",
        "completed",
        "start",
        "invitation-sent",
        "request-received",
        "response-sent",
        "abandoned",
        "completed",
    ]
    routing_state: Optional[str]
    state: Literal[
        "init", "invitation", "request", "response", "active", "inactive", "error"
    ]
    their_label: Optional[str] = None
    their_role: Literal["invitee", "requester", "inviter", "responder"]
    updated_at: str


class BasicMessagesHook(BaseModel):
    connection_id: str
    content: str
    message_id: str
    sent_time: str
    state: Literal["received"]


class ProofsHookV1(BaseModel):
    connection_id: Optional[str]
    created_at: str
    initiator: Literal["self", "external"]
    presentation_exchange_id: str
    presentation_request: dict
    presentation_request_dict: dict
    role: Literal["prover", "verifier"]
    state: Literal[
        "proposal_sent",
        "proposal_received",
        "request_sent",
        "request_received",
        "presentation_sent",
        "presentation_received",
        "verified",
    ]
    thread_id: str
    trace: bool
    updated_at: str


class ProofsHookV2(BaseModel):
    connection_id: Optional[str]
    created_at: str
    initiator: Literal["self", "external"]
    pres_ex_id: str
    pres_request: Optional[dict]
    role: Literal["prover", "verifier"]
    state: Literal[
        "proposal-sent",
        "proposal-received",
        "request-sent",
        "request-received",
        "presentation-sent",
        "presentation-received",
        "verified",
    ]
    thread_id: str
    trace: bool
    updated_at: str


class CredentialHookV2(BaseModel):
    auto_issue: Optional[bool]
    auto_offer: Optional[bool]
    auto_remove: Optional[bool]
    by_format: dict
    connection_id: Optional[str]
    created_at: str
    cred_ex_id: str
    cred_offer: Optional[dict]
    cred_preview: Optional[dict]
    cred_proposal: Optional[dict]
    initiator: Literal["self", "external"]
    role: Literal["issuer", "holder"]
    state: Optional[
        Literal[
            "proposal-sent",
            "proposal-received",
            "offer-sent",
            "offer-received",
            "request-sent",
            "request-received",
            "credential-issued",
            "credential-received",
            "done",
        ]
    ]
    thread_id: Optional[str]
    trace: bool
    updated_at: str


class CredentialHookV1(BaseModel):
    auto_issue: Optional[bool]
    auto_offer: Optional[bool]
    auto_remove: Optional[bool]
    connection_id: Optional[str]
    created_at: str
    credential_definition_id: str
    credential_exchange_id: Optional[str]
    credential_offer: Optional[dict]
    credential_proposal_dict: Optional[dict]
    initiator: Literal["self", "external"]
    role: Literal["issuer", "holder"]
    schema_id: Optional[str]
    state: Optional[
        Literal[
            "proposal_sent",
            "proposal_received",
            "offer_sent",
            "offer_received",
            "request_sent",
            "request_received",
            "credential_issued",
            "credential_received",
            "done",
        ]
    ]
    thread_id: Optional[str]
    trace: bool
    updated_at: str


class CredentialHooks(BaseModel):
    auto_issue: Optional[bool]
    auto_offer: Optional[bool]
    auto_remove: Optional[bool]
    connection_id: Optional[str]
    created_at: str
    protocol_version: Literal["v1", "v2"]
    initiator: Literal["self", "external"]
    role: Literal["issuer", "holder"]
    state: Optional[
        Literal[
            "proposal-sent",
            "proposal-received",
            "offer-sent",
            "offer-received",
            "request-sent",
            "request-received",
            "credential-issued",
            "credential-received",
            "done",
        ]
    ]
    thread_id: Optional[str]
    trace: bool
    updated_at: str
    credential_exchange_id: Optional[str]
    credential_definition_id: Optional[str]
    credential_proposal: Optional[dict]
    credential_offer: Optional[dict]

    # # v1
    # credential_offer: Optional[dict]
    # credential_proposal_dict: Optional[dict]
    # schema_id: Optional[str]
    # state: Optional[
    #     Literal[
    #         "proposal_sent",
    #         "proposal_received",
    #         "offer_sent",
    #         "offer_received",
    #         "request_sent",
    #         "request_received",
    #         "credential_issued",
    #         "credential_received",
    #         "done",
    #     ]
    # ]
    # # v2
    # by_format: dict
    # created_at: str
    # cred_ex_id: str
    # cred_offer: Optional[dict]
    # cred_preview: Optional[dict]
    # cred_proposal: Optional[dict]


def to_credentential_hook_model(item: dict) -> CredentialHooks:
    if "credential_exchange_id" in item:
        item["protocol_version"] = "v1"
        item["credential_exchange_id"] = "v1-" + item["credential_exchange_id"]
        item["credential_proposal"] = item["credential_proposal_dict"]
        try:
            item["state"] = item["state"].replace("_", "-")
        except KeyError:
            pass
        item = CredentialHooks(**item)
    else:
        item["protocol_version"] = "v2"
        item["cred_ex_id"] = "v2-" + item["cred_ex_id"]
        item["credential_exchange_id"] = item.pop("cred_ex_id")
        try:
            item["credential_definition_id"] = item["by_format"]["cred_offer"]["indy"][
                "cred_def_id"
            ]
        except KeyError:
            pass
        try:
            item["credential_offer"] = item["by_format"]["cred_offer"]
        except KeyError:
            pass
        try:
            item["credential_proposal"] = item["cred_proposal"]
        except KeyError:
            pass
        item = CredentialHooks(**item)

    return item


class TopicItem(BaseModel):
    topic: str
    payload: Any
