from typing import Optional

from aries_cloudcontroller import V10PresentationExchange, V20PresExRecord
from pydantic import BaseModel


class Presentation(BaseModel):
    V10: Optional[V10PresentationExchange] = None
    V20: Optional[V20PresExRecord] = None
