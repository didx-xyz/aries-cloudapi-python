from enum import Enum
from typing import Dict, Literal, Optional

from pydantic import BaseModel


class Credential(BaseModel):
    connection_id: str
    cred_def_id: str
    attributes: Dict[str, str]


class IssueCredentialProtocolVersion(Enum):
    v1 = "v1"
    v2 = "v2"


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
    ]
    # Attributes can be None in proposed state
    attributes: Optional[Dict[str, str]] = None
    # Connetion id can be None in connectionless exchanges
    connection_id: Optional[str] = None
