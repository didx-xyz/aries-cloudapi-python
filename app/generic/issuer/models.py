from typing import Dict

from pydantic import BaseModel


class Credential(BaseModel):
    connection_id: str
    cred_def_id: str
    attributes: Dict[str, str]
