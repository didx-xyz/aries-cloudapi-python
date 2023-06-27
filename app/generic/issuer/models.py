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


class IssueCredentialFacades(Enum):
    v1 = IssuerV1
    v2 = IssuerV2


class ProblemReportExplanation(TypedDict):
    description: str


class CredentialBase(BaseModel):
    protocol_version: IssueCredentialProtocolVersion
    credential_definition_id: str
    attributes: Dict[str, str]


class RevokeCredential(BaseModel):
    credential_definition_id: str = ""
    auto_publish_on_ledger: Optional[bool] = False
    credential_exchange_id: str = ""


class SendCredential(CredentialBase):
    connection_id: str


class CreateOffer(CredentialBase):
    pass


def issuer_from_id(id: str) -> Issuer:
    if id.startswith("v1-"):
        return IssueCredentialFacades.v1.value

    elif id.startswith("v2-"):
        return IssueCredentialFacades.v2.value

    raise CloudApiException(
        "Unknown version. ID is expected to contain protocol version", 400
    )


def issuer_from_protocol_version(version: IssueCredentialProtocolVersion) -> Issuer:
    facade = IssueCredentialFacades[version.name]

    return facade.value
