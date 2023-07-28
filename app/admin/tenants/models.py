from typing import List, Optional

from aries_cloudcontroller.model.wallet_record import WalletRecord
from pydantic import BaseModel, Field, HttpUrl

from app.facades.trust_registry import TrustRegistryRole


class WalletRecordWithGroups(WalletRecord):
    group_id: Optional[str] = Field(None, example="SomeGroupId")


class TenantRequestBase(BaseModel):
    image_url: Optional[HttpUrl] = Field(
        None, example="https://yoma.africa/images/sample.png"
    )


class CreateTenantRequest(TenantRequestBase):
    name: str = Field(..., example="Yoma")  # used as label and trust registry name
    roles: Optional[List[TrustRegistryRole]] = None
    group_id: Optional[str] = Field(None, example="SomeGroupId")


class UpdateTenantRequest(TenantRequestBase):
    name: Optional[str] = Field(
        None, example="Yoma"
    )  # used as label and trust registry name
    roles: Optional[List[TrustRegistryRole]] = None
    group_id: Optional[str] = Field(None, example="SomeGroupId")


class Tenant(BaseModel):
    tenant_id: str = Field(..., example="545135a4-ecbc-4400-8594-bdb74c51c88d")
    tenant_name: str = Field(..., example="Alice")
    image_url: Optional[str] = Field(None, example="https://yoma.africa/image.png")
    created_at: str = Field(...)
    updated_at: Optional[str] = Field(None)
    group_id: Optional[str] = Field(None, example="SomeGroupId")


class TenantAuth(BaseModel):
    access_token: str = Field(..., example="ey...")


class CreateTenantResponse(Tenant, TenantAuth):
    pass


def tenant_from_wallet_record(wallet_record: WalletRecordWithGroups) -> Tenant:
    label: str = wallet_record.settings["default_label"]
    image_url: Optional[str] = wallet_record.settings.get("image_url")

    return Tenant(
        tenant_id=wallet_record.wallet_id,
        tenant_name=label,
        image_url=image_url,
        created_at=wallet_record.created_at,
        updated_at=wallet_record.updated_at,
        group_id=wallet_record.group_id if hasattr(wallet_record, "group_id") else None,
    )
