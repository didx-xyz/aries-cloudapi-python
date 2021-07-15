import logging

from dependencies import agent_selector

from aries_cloudcontroller import AriesAgentControllerBase
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generic/issuers/v1", tags=["issuer"])


class Credential(BaseModel):
    connection_id: str
    schema_id: str
    cred_def_id: str
    attributes: List[str]
    comment: str = ""
    auto_remove: bool = False
    trace: bool = False


class CredentialOffer(BaseModel):
    connection_id: str
    cred_def_id: str
    attributes: List[str]
    comment: str = ""
    auto_issue: bool = True
    auto_remove: bool = True
    trace: bool = False


@router.post("/credential", tags=["issuer", "credential"])
async def send_credential(
    Credential,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    return await aries_controller.issuer.send_credential(**Credential.dict())


@router.get("/x-controls", tags=["issuer", "credential"])
async def controls(
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    pass


@router.get("/credential", tags=["issuer", "credential"])
async def get_credential(
    credential_id: str,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    return await aries_controller.issuer.get_record_by_id(credential_id)


@router.delete("/credential", tags=["issuer", "credential"])
async def remove_credential(
    credential_id: str,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    return await aries_controller.credentials.remove_credential(credential_id)


@router.post("/problem-report", tags=["issuer", "credential"])
async def problem_report(
    credential_x_id: str,
    explanation: str,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    return await aries_controller.issuer.send_problem_report(
        credential_x_id, explanation
    )


@router.post("/credential/offer", tags=["issuer", "credential"])
async def send_offer(
    CredentialOffer,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    return await aries_controller.issuer.send_offer(**CredentialOffer.dict())


@router.post("/credential/request", tags=["issuer", "credential"])
async def credential_request(
    credential_x_id: str,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    return await aries_controller.issuer.send_request_for_record(credential_x_id)


@router.get("/credential/store", tags=["issuer", "credential"])
async def store_credential(
    credential_x_id: str,
    credential_id: str = None,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    return await aries_controller.issuer.store_credential(
        credential_x_id, credential_id
    )


@router.get("/credential/proposal", tags=["issuer", "credential"])
async def send_credential_proposal(
    Credential,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    return await aries_controller.issuer.send_proposal(**Credential.dict())
