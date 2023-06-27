from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel
from typing_extensions import TypedDict

from app.generic.issuer.facades.acapy_issuer import Issuer
from app.generic.issuer.facades.acapy_issuer_v1 import IssuerV1
from app.generic.issuer.facades.acapy_issuer_v2 import IssuerV2
from shared import IssueCredentialProtocolVersion
from shared.cloud_api_error import CloudApiException


class Credential(BaseModel):
    connection_id: str
    cred_def_id: str
    attributes: Dict[str, str]


class CredentialNoConnection(BaseModel):
    cred_def_id: str
    attributes: Dict[str, str]
