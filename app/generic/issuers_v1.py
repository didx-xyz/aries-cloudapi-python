import logging

from dependencies import agent_selector

from aries_cloudcontroller import AriesAgentControllerBase
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List
from facade import (
    get_connection_id,
    get_cred_def_id,
    get_schema_attributes,
    issue_credentials,
    write_credential_def,
)
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from schemas import ConnectionIdResponse, IssueCredentialResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generic/issuers/v1", tags=["issuer"])


class CredentialHelper(BaseModel):
    schema_id: str
    connection_id: str
    credential_attrs: List[str] = Query(None)


class CredentialOffer(BaseModel):
    connection_id: str
    attributes: List[str]
    cred_def_id: str = None
    comment: str = ""
    auto_issue: bool = True
    auto_remove: bool = True
    trace: bool = False


@router.post("/credential", tags=["issuer", "credential"])
async def send_credential(
    CredentialHelper,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    schema_attr = await get_schema_attributes(
        aries_controller, CredentialHelper.schema_id
    )
    credential_def = await write_credential_def(
        aries_controller, CredentialHelper.schema_id
    )

    cred_def_id = await get_cred_def_id(aries_controller, credential_def)
    credential_attributes = [
        {"name": k, "value": v}
        for k, v in list(zip(schema_attr, CredentialHelper.credential_attrs))
    ]
    record = await issue_credentials(
        aries_controller,
        CredentialHelper.connection_id,
        CredentialHelper.schema_id,
        cred_def_id,
        credential_attributes,
    )
    response = IssueCredentialResponse(credential=record)
    return response
    # return await aries_controller.issuer.send_credential(**Credential.dict())


@router.get("/records", tags=["issuer", "credential"])
async def get_records(
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    return await aries_controller.issuer.get_records()


@router.get("/credential", tags=["issuer", "credential"])
async def get_x_record(
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
async def send_credential_request(
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
