import logging

from dependencies import agent_selector
from facade import (
    issue_credentials,
    get_schema_attributes,
    write_credential_def,
    get_cred_def_id,
)
from aries_cloudcontroller import AriesAgentControllerBase
from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from typing import List, Optional
from schemas import IssueCredentialResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generic/issuers/v2", tags=["issuer_v2"])


class Credential(BaseModel):
    connection_id: str
    schema_id: str
    cred_def_id: str
    attributes: List[str]


class CredentialOffer(BaseModel):
    connection_id: str
    cred_def_id: str
    attributes: List[str]
    comment: str = ""
    auto_issue: bool = True
    auto_remove: bool = True
    trace: bool = False


class Proposal(BaseModel):
    connection_id: str
    schema_id: str
    cred_def_id: str
    attributes: List[str]
    comment: str = ""
    auto_remove: bool = True
    trace: bool = False


@router.get("/records")
async def get_records(
    connection_id: Optional[str] = Header(None),
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    return await aries_controller.issuer_v2.get_records(connection_id=connection_id)


@router.post("/credential")
async def send_credential(
    credential: Credential,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):

    return await aries_controller.issuer_v2.send_credential(**credential)


@router.get("/credential")
async def get_credential(
    credential_id: str,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    # Same as in v1
    return await aries_controller.issuer.get_record_by_id(credential_id)


@router.delete("/credential")
async def remove_credential(
    credential_id: str,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    # Same as in v1
    return await aries_controller.credentials.remove_credential(credential_id)


@router.post("/problem-report")
async def problem_report(
    credential_x_id: str,
    explanation: str,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    return await aries_controller.issuer_v2.problem_report(credential_x_id, explanation)


@router.post("/credential/offer")
async def send_offer(
    credential_offer: CredentialOffer,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    return await aries_controller.issuer_v2.send_offer(**credential_offer.dict())


@router.post("/credential/request")
async def credential_request(
    credential_x_id: str,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    return await aries_controller.issuer_v2.send_request_for_record(credential_x_id)


@router.get("/credential/store")
async def store_credential(
    credential_x_id: str,
    credential_id: str = None,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    return await aries_controller.issuer_v2.store_credential(
        credential_x_id, credential_id
    )


@router.get("/credential/proposal")
async def send_credential_proposal(
    proposal: Proposal,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    return await aries_controller.issuer_v2.send_proposal(**proposal.dict())


@router.get("/credential/cred_req_no_thread")
async def send_credential_request_no_thread(
    Credential,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    # Not sure how this works yet
    pass
