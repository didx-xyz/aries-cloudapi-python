from typing import Optional

from aries_cloudcontroller import AriesAgentControllerBase
from dependencies import agent_selector
from fastapi import APIRouter, Depends
from pydantic import BaseModel

router = APIRouter(
    prefix="/admin/governance/credential-definitions", tags=["CredentialDefinitions"]
)


class CredentialDefinition(BaseModel):
    support_revocation: Optional[bool]
    tag: str
    schema_id: str


@router.post("/")
async def create_credential_definition(
    credential_definition: CredentialDefinition,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    credential_definition_result = await aries_controller.definitions.write_cred_def(
        **credential_definition.dict()
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
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    return await aries_controller.definitions.search_created(
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
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    return await aries_controller.definitions.get_by_id(cred_def_id)
