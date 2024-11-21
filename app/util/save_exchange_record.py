from typing import Optional

from pydantic import BaseModel, Field

save_exchange_record_field = Field(
    default=None,
    description=(
        "Controls exchange record retention after exchange is complete. None uses "
        "wallet default (typically to delete), true forces save, false forces delete."
    ),
)


class SaveExchangeRecordField(BaseModel):
    save_exchange_record: Optional[bool] = save_exchange_record_field

    @property
    def auto_remove(self) -> Optional[bool]:
        """Returns the inverse of save_exchange_record if set, otherwise None."""
        if self.save_exchange_record is None:
            return None
        return not self.save_exchange_record
