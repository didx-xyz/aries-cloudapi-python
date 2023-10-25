from typing import List, Optional

from aries_cloudcontroller import CreateWalletRequest
from pydantic import BaseModel, Field

from app.services.trust_registry import TrustRegistryRole


class CreateWalletRequestWithGroups(CreateWalletRequest):
    group_id: Optional[str] = None


class TenantRequestBase(BaseModel):
    image_url: Optional[str] = Field(
        None, examples=["https://yoma.africa/images/sample.png"]
    )


class CreateTenantRequest(TenantRequestBase):
    name: str = Field(..., examples=["Yoma"])  # used as label and trust registry name
    roles: Optional[List[TrustRegistryRole]] = None
    group_id: Optional[str] = Field(None, examples=["SomeGroupId"])


class UpdateTenantRequest(TenantRequestBase):
    name: Optional[str] = Field(
        None, examples=["Yoma"]
    )  # used as label and trust registry name
    roles: Optional[List[TrustRegistryRole]] = None
    group_id: Optional[str] = Field(None, examples=["SomeGroupId"])


class Tenant(BaseModel):
    wallet_id: str = Field(..., examples=["545135a4-ecbc-4400-8594-bdb74c51c88d"])
    tenant_name: str = Field(..., examples=["Alice"])
    image_url: Optional[str] = Field(None, examples=["https://yoma.africa/image.png"])
    created_at: str = Field(...)
    updated_at: Optional[str] = Field(None)
    group_id: Optional[str] = Field(None, examples=["SomeGroupId"])


class TenantAuth(BaseModel):
    access_token: str = Field(..., examples=["ey..."])


class CreateTenantResponse(Tenant, TenantAuth):
    pass


class OnboardResult(BaseModel):
    did: str
    didcomm_invitation: Optional[str] = None
