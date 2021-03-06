import logging
from enum import Enum
from typing import Dict, Optional

from aries_cloudcontroller import AcaPyClient
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

# TypedDict from typing itself has some missing features for pydantic only available in 3.9
# https://pydantic-docs.helpmanual.io/usage/types/#typeddict
from typing_extensions import TypedDict

from app.dependencies import agent_selector
from app.error.cloud_api_error import CloudApiException
from app.facades.acapy_ledger import schema_id_from_credential_definition_id
from app.facades.acapy_wallet import assert_public_did
from app.facades.trust_registry import assert_valid_issuer
from app.generic.issuer.facades.acapy_issuer import Issuer
from app.generic.issuer.facades.acapy_issuer_v1 import IssuerV1
from app.generic.issuer.facades.acapy_issuer_v2 import IssuerV2
from app.generic.issuer.models import Credential
from app.util.indy import did_from_credential_definition_id
from shared_models import IssueCredentialProtocolVersion

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generic/issuer", tags=["issuer"])


class IssueCredentialFacades(Enum):
    v1 = IssuerV1
    v2 = IssuerV2


class ProblemReportExplanation(TypedDict):
    description: str


class SendCredential(BaseModel):
    protocol_version: IssueCredentialProtocolVersion
    connection_id: str
    credential_definition_id: str
    attributes: Dict[str, str]


def __issuer_from_id(id: str) -> Issuer:
    if id.startswith("v1-"):
        return IssueCredentialFacades.v1.value

    elif id.startswith("v2-"):
        return IssueCredentialFacades.v2.value

    raise Exception("Unknown version. ID is expected to contain protocol version")


def __issuer_from_protocol_version(version: IssueCredentialProtocolVersion) -> Issuer:
    facade = IssueCredentialFacades[version.name]

    return facade.value


@router.get("/credentials")
async def get_credentials(
    connection_id: Optional[str] = Query(None),
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Get list of records.

    Parameters:
    ------------
    connection_id: str (Optional)
    """

    v1_records = await IssueCredentialFacades.v1.value.get_records(
        controller=aries_controller, connection_id=connection_id
    )

    v2_records = await IssueCredentialFacades.v2.value.get_records(
        controller=aries_controller, connection_id=connection_id
    )

    return v1_records + v2_records


@router.get("/credentials/{credential_id}")
async def get_credential(
    credential_id: str,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Get credential by credential id.

    Parameters:
    -----------
    credential_id: str
        credential identifier
    """

    issuer = __issuer_from_id(credential_id)

    return await issuer.get_record(
        controller=aries_controller, credential_exchange_id=credential_id
    )


@router.post("/credentials")
async def send_credential(
    credential: SendCredential,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Create and send credential. Automating the entire flow.

    Parameters:
    ------------
    credential: Credential
        payload for sending a credential

    Returns:
    --------
    The response object from sending a credential
    """

    issuer = __issuer_from_protocol_version(credential.protocol_version)

    # Assert the agent has a public did
    public_did = await assert_public_did(aries_controller)

    # Retrieve the schema_id based on the credential definition id
    schema_id = await schema_id_from_credential_definition_id(
        aries_controller, credential.credential_definition_id
    )

    # Make sure we are allowed to issue according to trust registry rules
    await assert_valid_issuer(public_did, schema_id)

    return await issuer.send_credential(
        controller=aries_controller,
        credential=Credential(
            attributes=credential.attributes,
            cred_def_id=credential.credential_definition_id,
            connection_id=credential.connection_id,
        ),
    )


@router.delete("/credentials/{credential_id}", status_code=204)
async def remove_credential(
    credential_id: str,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Remove credential.

    Parameters:
    -----------
    credential_id: str
        credential identifier

    Returns:
    --------
    The response object from removing a credential.

    """
    issuer = __issuer_from_id(credential_id)

    await issuer.delete_credential(
        controller=aries_controller, credential_exchange_id=credential_id
    )


@router.post("/credentials/{credential_id}/request")
async def request_credential(
    credential_id: str,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Send credential request.

    Parameters:
    -----------
    credential_id: str
        credential id
    """
    issuer = __issuer_from_id(credential_id)

    record = await issuer.get_record(aries_controller, credential_id)

    if not record.credential_definition_id or not record.schema_id:
        raise CloudApiException(
            "Record has no credential definition or schema associated. "
            "This proably means you haven't received an offer yet.",
            403,
        )

    did = did_from_credential_definition_id(record.credential_definition_id)

    # Make sure the issuer is allowed to issue this credential according to trust registry rules
    await assert_valid_issuer(f"did:sov:{did}", record.schema_id)

    return await issuer.request_credential(
        controller=aries_controller, credential_exchange_id=credential_id
    )


@router.post("/credentials/{credential_id}/store")
async def store_credential(
    credential_id: str,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Store credential.

    Parameters:
    -----------
    credential_id: str
        credential identifier

    """
    issuer = __issuer_from_id(credential_id)

    return await issuer.store_credential(
        controller=aries_controller, credential_exchange_id=credential_id
    )
