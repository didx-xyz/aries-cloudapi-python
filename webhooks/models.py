from typing import Any, Optional
from typing_extensions import Literal
from pydantic import BaseModel, ValidationError


class HookBase(BaseModel):
    wallet_id: Optional[str]


class ConnectionsHook(HookBase):
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


def to_connections_model(item: dict):
    if item["connection_protocol"] == "didexchange/1.0":
        item["connection_id"] = "0023-" + item["connection_id"]
    elif item["connection_protocol"] == "connections/1.0":
        item["connection_id"] = "0016-" + item["connection_id"]
    try:
        item = ConnectionsHook(**item)
    except ValidationError:
        pass
    return item


class BasicMessagesHook(HookBase):
    connection_id: str
    content: str
    message_id: str
    sent_time: str
    state: Literal["received"]


class ProofsHook(HookBase):
    connection_id: Optional[str]
    created_at: str
    initiator: Literal["self", "external"]
    role: Literal["prover", "verifier"]
    protocol_version: Literal["v1", "v2"]
    presentation_exchange_id: str
    presentation_request: Optional[dict]
    presentation_request_dict: Optional[dict]
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


def to_proof_hook_model(item: dict) -> ProofsHook:
    if "presentation_exchange_id" in item:
        item["protocol_version"] = "v1"
        item["presentation_exchange_id"] = "v1-" + item["presentation_exchange_id"]
        try:
            item["state"] = item["state"].replace("_", "-")
        except KeyError:
            pass
        item["presentation_exchange_id"] = "v1-" + item["presentation_exchange_id"]
        item = ProofsHook(**item)
    elif "pres_ex_id" in item:
        item["pres_ex_id"] = "v2-" + item["pres_ex_id"]
        item["presentation_exchange_id"] = item.pop("pres_ex_id")
        item["protocol_version"] = "v2"
        item["presentation_request"] = item.pop("pres_request")
        item = ProofsHook(**item)
    return item


class CredentialHooks(HookBase):
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
    elif "cred_ex_id" in item:
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
