from typing import Any, List, Optional, Union

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
    extra_settings: Optional[Union[str, Any]] = None


class UpdateTenantRequest(BaseModel):
    wallet_label: Optional[str] = Field(
        None, description=label_description, examples=label_examples
    )
    roles: Optional[List[TrustRegistryRole]] = None
    group_id: Optional[str] = group_id_field
    image_url: Optional[str] = image_url_field
    extra_settings: Optional[Union[str, Any]] = None


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
