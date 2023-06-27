from enum import Enum

from app.exceptions.cloud_api_error import CloudApiException
from app.generic.issuer.facades.acapy_issuer import Issuer
from app.generic.issuer.facades.acapy_issuer_v1 import IssuerV1
from app.generic.issuer.facades.acapy_issuer_v2 import IssuerV2
from shared.models.protocol import IssueCredentialProtocolVersion


class IssueCredentialFacades(Enum):
    v1 = IssuerV1
    v2 = IssuerV2


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
