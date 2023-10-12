from typing import List, Literal, Optional

from typing_extensions import TypedDict

TrustRegistryRole = Literal["issuer", "verifier"]


class Actor(TypedDict):
    id: str
    name: str
    roles: List[TrustRegistryRole]
    did: str
    didcomm_invitation: Optional[str]


class Schema(TypedDict):
    did: str
    name: str
    version: str
    id: str
