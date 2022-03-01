from typing import Optional

from aries_cloudcontroller import AcaPyClient, CredentialDefinitionSendRequest
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.dependencies import agent_selector

router = APIRouter(
    prefix="/admin/governance/credential-definitions",
    tags=["admin: credential definitions"],
)


class CredentialDefinition(BaseModel):
    support_revocation: Optional[bool]
    tag: str
    schema_id: str


@router.post("/")
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
    return await aries_controller.credential_definition.publish_cred_def(
        body=CredentialDefinitionSendRequest(**credential_definition.dict())
    )
