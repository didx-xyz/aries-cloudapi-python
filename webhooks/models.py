from typing import Any, Optional, Dict, List
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


def to_connections_model(item: dict) -> ConnectionsHook:
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
    proof_id: str
    presentation: Optional[dict]
    presentation_request: Optional[dict]
    protocol_version: Literal["v1", "v2"]
    role: Literal["prover", "verifier"]
    state: Literal[
        "proposal-sent",
        "proposal-received",
        "request-sent",
        "request-received",
        "presentation-sent",
        "presentation-received",
        "verified",
        "done",
        "abandoned",
    ]
    updated_at: str
    verified: Optional[bool] = None


def to_proof_hook_model(item: dict) -> ProofsHook:
    if "presentation_exchange_id" in item:
        item["protocol_version"] = "v1"
        item["proof_id"] = "v1-" + item["presentation_exchange_id"]
        try:
            item["state"] = item["state"].replace("_", "-")
        except KeyError:
            pass
    elif "pres_ex_id" in item:
        item["proof_id"] = "v2-" + item["pres_ex_id"]
        item["presentation_exchange_id"] = item.pop("pres_ex_id")
        item["protocol_version"] = "v2"
        item["presentation"] = item.pop("pres_request")
    try:
        item["presentation_request"] = item.pop("presentation_request_dict")
    except KeyError:
        pass
    return ProofsHook(**item)


class CredentialsHooks(HookBase):
    credential_id: Optional[str]
    role: Literal["issuer", "holder"]
    created_at: str
    updated_at: str
    protocol_version: Literal["v1", "v2"]
    schema_id: Optional[str]
    credential_definition_id: Optional[str]
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
            "credential-acked",
            "done",
        ]
    ] = None
    attributes: Optional[List[Dict]]
    connection_id: Optional[str]
    credential_proposal: Optional[dict]


def to_credentential_hook_model(item: dict) -> CredentialsHooks:
    if "credential_exchange_id" in item:
        item["protocol_version"] = "v1"
        item["credential_id"] = "v1-" + item["credential_exchange_id"]
        item["credential_proposal"] = item["credential_proposal_dict"]
        try:
            item["state"] = item["state"].replace("_", "-")
        except KeyError:
            pass
    elif "cred_ex_id" in item:
        item["protocol_version"] = "v2"
        item["cred_ex_id"] = "v2-" + item["cred_ex_id"]
        item["credential_id"] = item.pop("cred_ex_id")
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
    try:
        item["attributes"] = item["credential_proposal"]["credential_proposal"][
            "attributes"
        ]
    except (KeyError, TypeError):
        pass
    return CredentialsHooks(**item)


class TopicItem(BaseModel):
    topic: str
    payload: Any
