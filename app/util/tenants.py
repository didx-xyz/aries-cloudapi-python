from typing import Optional

from app.models.tenants import Tenant, WalletRecordWithGroups


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
