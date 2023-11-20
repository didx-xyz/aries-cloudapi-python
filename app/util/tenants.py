import base64
import json
from typing import Optional

from aries_cloudcontroller import WalletRecordWithGroups

from app.models.tenants import Tenant


def tenant_from_wallet_record(wallet_record: WalletRecordWithGroups) -> Tenant:
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


def get_wallet_id_from_b64encoded_jwt(jwt: str) -> str:
    # Add padding if required
    # b64 needs lengths divisible by 4
    if len(jwt) % 4 != 0:
        n_missing = 4 - (len(jwt) % 4)
        jwt = jwt + (n_missing * "=")

    wallet = json.loads(base64.b64decode(jwt))
    return wallet["wallet_id"]

