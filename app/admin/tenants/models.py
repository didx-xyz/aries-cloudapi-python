from typing import List, Optional
from aries_cloudcontroller.model.wallet_record import WalletRecord
from pydantic import BaseModel, Field, HttpUrl

from app.facades.trust_registry import TrustRegistryRole


class TenantRequestBase(BaseModel):
    image_url: Optional[HttpUrl] = Field(
        None, example="https://www.hyperledger.org/wp-content/uploads/2019/06/Hyperledger_Aries_Logo_Color.png"
    )


class CreateTenantRequest(TenantRequestBase):
    name: str = Field(..., example="Governance")  # used as label and trust registry name
    roles: Optional[List[TrustRegistryRole]] = None


class UpdateTenantRequest(TenantRequestBase):
    name: Optional[str] = Field(
        None, example="Governance"
    )  # used as label and trust registry name
    roles: Optional[List[TrustRegistryRole]] = None


class Tenant(BaseModel):
    tenant_id: str = Field(..., example="545135a4-ecbc-4400-8594-bdb74c51c88d")
    tenant_name: str = Field(..., example="Alice")
    image_url: Optional[str] = Field(None, example="https://www.hyperledger.org/wp-content/uploads/2019/06/Hyperledger_Aries_Logo_Color.png")
    created_at: str = Field(...)
    updated_at: Optional[str] = Field(None)


class TenantAuth(BaseModel):
    access_token: str = Field(..., example="ey...")


class CreateTenantResponse(Tenant, TenantAuth):
    pass


def tenant_from_wallet_record(wallet_record: WalletRecord) -> Tenant:
    label: str = wallet_record.settings["default_label"]
    image_url: Optional[str] = wallet_record.settings["image_url"]

    return Tenant(
        tenant_id=wallet_record.wallet_id,
        tenant_name=label,
        image_url=image_url,
        created_at=wallet_record.created_at,
        updated_at=wallet_record.updated_at,
    )
