from typing import Optional

from aries_cloudcontroller import (
    AcaPyClient,
    CredentialDefinitionSendRequest,
    TxnOrCredentialDefinitionSendResult,
)
from dependencies import agent_selector
from fastapi import APIRouter, Depends
from pydantic import BaseModel

router = APIRouter(
    prefix="/admin/governance/credential-definitions",
    tags=["admin: credentialdefinitions"],
)


class CredentialDefinition(BaseModel):
    support_revocation: Optional[bool]
    tag: str
    schema_id: str


@router.post("/", response_model=TxnOrCredentialDefinitionSendResult)
async def create_credential_definition(
    credential_definition: CredentialDefinition,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Create a credential definition.

    Parameters:
    -----------
    credential_definition: CredentialDefinition
        Payload for creating a credential definition.

    Returns:
    --------
    The response object obtained from creating a credential definition.
    """
    credential_definition_result = (
        await aries_controller.credential_definition.publish_cred_def(
            body=CredentialDefinitionSendRequest(**credential_definition.dict())
        )
    )
    return credential_definition_result


@router.get("/created")
async def get_created_credential_definitions(
    issuer_did: Optional[str] = None,
    cred_def_id: Optional[str] = None,
    schema_id: Optional[str] = None,
    schema_issuer_did: Optional[str] = None,
    schema_name: Optional[str] = None,
    schema_version: Optional[str] = None,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Retrieve credential definitions the current agent created.

    Parameters:
    -----------
    issuer_did: str (Optional)
    cred_def_id: str (Optional)
    credential definition id
    schema_id: str (Optional)
    schema_issuer_id: str (Optional)
    schema_version: str (Optional)

    Returns:
    ---------
    The created credential definitions.
    """
    return await aries_controller.credential_definition.get_created_cred_defs(
        issuer_did=issuer_did,
        cred_def_id=cred_def_id,
        schema_id=schema_id,
        schema_issuer_did=schema_issuer_did,
        schema_name=schema_name,
        schema_version=schema_version,
    )


@router.get("/{cred_def_id}")
async def get_credential_definition(
    cred_def_id: str,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Get credential definitions by id.

    Parameters:
    -----------
    cred_def_id: str
        credential definition id

    """
    return await aries_controller.credential_definition.get_cred_def(
        cred_def_id=cred_def_id
    )
