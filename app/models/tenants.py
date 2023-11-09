from typing import Dict, List, Literal, Optional

from aries_cloudcontroller import CreateWalletRequest
from pydantic import BaseModel, Field

from app.models.trust_registry import TrustRegistryRole

# Deduplicate some descriptions and field definitions
label_description = "A required alias for the tenant, publicized to other agents when forming a connection. "
"If the tenant is an issuer or verifier, this label will be displayed on the trust registry and must be unique."
label_examples = ["Tenant Label"]
group_id_field = Field(
    None,
    description="An optional group identifier. Useful with `get_tenants` to fetch wallets by group id.",
    examples=["Some Group Id"],
)
image_url_field = Field(
    None,
    examples=["https://upload.wikimedia.org/wikipedia/commons/7/70/Example.png"],
)
ExtraSettings = Literal[
    "ACAPY_LOG_LEVEL",
    "ACAPY_INVITE_PUBLIC",
    "ACAPY_PUBLIC_INVITES",
    "ACAPY_AUTO_ACCEPT_INVITES",
    "ACAPY_AUTO_ACCEPT_REQUESTS",
    "ACAPY_AUTO_PING_CONNECTION",
    "ACAPY_MONITOR_PING",
    "ACAPY_AUTO_RESPOND_MESSAGES",
    "ACAPY_AUTO_RESPOND_CREDENTIAL_OFFER",
    "ACAPY_AUTO_RESPOND_CREDENTIAL_REQUEST",
    "ACAPY_AUTO_VERIFY_PRESENTATION",
    "ACAPY_NOTIFY_REVOCATION",
    "ACAPY_AUTO_REQUEST_ENDORSEMENT",
    "ACAPY_AUTO_WRITE_TRANSACTIONS",
    "ACAPY_CREATE_REVOCATION_TRANSACTIONS",
    "ACAPY_ENDORSER_ROLE",
]
ExtraSettings_field = Field(
    None,
    description="Accepted ACAPY config fields. The extra_settings field is optional",
    examples=[{
      "ACAPY_LOG_LEVEL":"str",
      "ACAPY_INVITE_PUBLIC":"str",
      "ACAPY_PUBLIC_INVITES":"str",
      "ACAPY_AUTO_ACCEPT_INVITES":"str",
      "ACAPY_AUTO_ACCEPT_REQUESTS":"str",
      "ACAPY_AUTO_PING_CONNECTION":"str",
      "ACAPY_MONITOR_PING":"str",
      "ACAPY_AUTO_RESPOND_MESSAGES":"str",
      "ACAPY_AUTO_RESPOND_CREDENTIAL_OFFER":"str",
      "ACAPY_AUTO_RESPOND_CREDENTIAL_REQUEST":"str",
      "ACAPY_AUTO_VERIFY_PRESENTATION":"str",
      "ACAPY_NOTIFY_REVOCATION":"str",
      "ACAPY_AUTO_REQUEST_ENDORSEMENT":"str",
      "ACAPY_AUTO_WRITE_TRANSACTIONS":"str",
      "ACAPY_CREATE_REVOCATION_TRANSACTIONS":"str",
      "ACAPY_ENDORSER_ROLE":"str",
    }]    
)

class CreateWalletRequestWithGroups(CreateWalletRequest):
    group_id: Optional[str] = group_id_field


class CreateTenantRequest(BaseModel):
    wallet_label: str = Field(
        ..., description=label_description, examples=label_examples
    )
    wallet_name: Optional[str] = Field(
        None,
        description="An optional wallet name. Useful with `get_tenants` to fetch wallets by wallet name. "
        "If selected, must be unique. Otherwise, randomly generated.",
        examples=["Unique name"],
    )
    roles: Optional[List[TrustRegistryRole]] = None
    group_id: Optional[str] = group_id_field
    image_url: Optional[str] = image_url_field
    extra_settings: Optional[Dict[ExtraSettings, str]] = ExtraSettings_field


class UpdateTenantRequest(BaseModel):
    wallet_label: Optional[str] = Field(
        None, description=label_description, examples=label_examples
    )
    roles: Optional[List[TrustRegistryRole]] = None
    group_id: Optional[str] = group_id_field
    image_url: Optional[str] = image_url_field
    extra_settings: Optional[Dict[ExtraSettings, str]] = ExtraSettings_field


class Tenant(BaseModel):
    wallet_id: str = Field(..., examples=["545135a4-ecbc-4400-8594-bdb74c51c88d"])
    wallet_label: str = Field(..., examples=["Alice"])
    wallet_name: str = Field(..., examples=["SomeWalletName"])
    created_at: str = Field(...)
    updated_at: Optional[str] = Field(None)
    image_url: Optional[str] = image_url_field
    group_id: Optional[str] = group_id_field


class TenantAuth(BaseModel):
    access_token: str = Field(..., examples=["ey..."])


class CreateTenantResponse(Tenant, TenantAuth):
    pass


class OnboardResult(BaseModel):
    did: str
    didcomm_invitation: Optional[str] = None
