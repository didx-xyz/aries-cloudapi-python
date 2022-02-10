from typing import Any, Optional, List, Dict
from typing_extensions import Literal
from pydantic import BaseModel


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


class TopicItem(BaseModel):
    topic: str
    payload: Any
