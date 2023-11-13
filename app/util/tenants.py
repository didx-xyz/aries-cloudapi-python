from typing import Any, Optional

# from aries_cloudcontroller import WalletRecordWithGroups

from app.models.tenants import Tenant


def tenant_from_wallet_record(wallet_record: Any) -> Tenant:
    label: str = wallet_record.settings["default_label"]
    wallet_name: str = wallet_record.settings["wallet.name"]
    image_url: Optional[str] = wallet_record.settings.get("image_url")
    group_id: Optional[str] = (
        wallet_record.group_id if hasattr(wallet_record, "group_id") else None
    )

    return Tenant(
        wallet_id=wallet_record.wallet_id,
        wallet_label=label,
        wallet_name=wallet_name,
        created_at=wallet_record.created_at,
        updated_at=wallet_record.updated_at,
        image_url=image_url,
        group_id=group_id,
    )
