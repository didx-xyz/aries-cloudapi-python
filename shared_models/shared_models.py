from enum import Enum
from typing import Optional, Dict, Literal

from aries_cloudcontroller import (
    IndyProof,
    IndyProofRequest,
)
from pydantic import BaseModel


class ProofRequestProtocolVersion(Enum):
    v1 = "v1"
    v2 = "v2"


class IssueCredentialProtocolVersion(Enum):
    v1 = "v1"
    v2 = "v2"


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


class CredentialExchange(BaseModel):
    credential_id: str
    role: Literal["issuer", "holder"]
    created_at: str
    updated_at: str
    protocol_version: IssueCredentialProtocolVersion
    schema_id: Optional[str]
    credential_definition_id: Optional[str]
    state: Literal[
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
        "credential-acked",
    ]
    # Attributes can be None in proposed state
    attributes: Optional[Dict[str, str]] = None
    # Connetion id can be None in connectionless exchanges
    connection_id: Optional[str] = None


class PresentationExchange(BaseModel):
    connection_id: Optional[str] = None
    created_at: str
    proof_id: str
    presentation: Optional[IndyProof] = None
    presentation_request: Optional[IndyProofRequest] = None
    protocol_version: ProofRequestProtocolVersion
    role: Literal["prover", "verifier"]
    state: Literal[
        "proposal-sent",
        "proposal-received",
        "request-sent",
        "request-received",
        "presentation-sent",
        "presentation-received",
        "done",
        "abandoned",
    ]
    updated_at: Optional[str] = None
    verified: Optional[bool] = None


class TopicItem(BaseModel):
    topic: str
    wallet_id: str = None
    origin: str = None
    payload: dict


class HookBase(BaseModel):
    wallet_id: Optional[str]
    origin: Optional[str]
