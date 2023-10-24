from typing import List, Optional

from aries_cloudcontroller import CreateWalletRequest
from pydantic import BaseModel, Field

from app.models.trust_registry import TrustRegistryRole

# Deduplicate some descriptions and field definitions
name_description = "A required alias for the tenant, publicized to other agents when forming a connection. "
"If the tenant is an issuer or verifier, this name will be displayed on the trust registry and must be unique."
name_examples = ["A required alias for the tenant"]
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
    name: str = Field(..., description=name_description, examples=name_examples)
    wallet_name: Optional[str] = Field(
        None,
        description="An optional wallet name. Useful with `get_tenants` to fetch wallets by wallet name. "
        "If selected, must be unique.",
        examples=["An optional, unique wallet name"],
    )
    roles: Optional[List[TrustRegistryRole]] = None
    group_id: Optional[str] = group_id_field
    image_url: Optional[str] = image_url_field


class UpdateTenantRequest(BaseModel):
    name: Optional[str] = Field(
        None, description=name_description, examples=name_examples
    )
    roles: Optional[List[TrustRegistryRole]] = None
    group_id: Optional[str] = group_id_field
    image_url: Optional[str] = image_url_field


class Tenant(BaseModel):
    wallet_id: str = Field(..., examples=["545135a4-ecbc-4400-8594-bdb74c51c88d"])
    tenant_name: str = Field(..., examples=["Alice"])
    image_url: Optional[str] = image_url_field
    created_at: str = Field(...)
    updated_at: Optional[str] = Field(None)
    group_id: Optional[str] = group_id_field


class TenantAuth(BaseModel):
    access_token: str = Field(..., examples=["ey..."])


class CreateTenantResponse(Tenant, TenantAuth):
    pass


class OnboardResult(BaseModel):
    did: str
    didcomm_invitation: Optional[str] = None
