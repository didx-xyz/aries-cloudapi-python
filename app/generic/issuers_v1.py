import logging

from dependencies import agent_selector

from aries_cloudcontroller import AriesAgentControllerBase
from pydantic import BaseModel
from typing import List
from facade import (
    get_cred_def_id,
    get_schema_attributes,
    issue_credentials,
    write_credential_def,
)
from fastapi import APIRouter, Depends
from schemas import IssueCredentialResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generic/issuers/v1", tags=["issue-credential v1"])


class CredentialHelper(BaseModel):
    schema_id: str
    connection_id: str
    credential_attrs: List[str]
    comment: str = ""
    auto_issue: bool = True
    auto_remove: bool = False
    trace: bool = False


class CredentialOffer(BaseModel):
    connection_id: str
    cred_def_id: str
    attributes: List[str]
    comment: str = ""
    auto_issue: bool = True
    auto_remove: bool = False
    trace: bool = False


async def _credential_details(credential_helper, aries_controller):
    schema_attr = await get_schema_attributes(
        aries_controller, credential_helper.schema_id
    )
    credential_def = await write_credential_def(
        aries_controller, credential_helper.schema_id
    )

    cred_def_id = await get_cred_def_id(aries_controller, credential_def)
    credential_attributes = [
        {"name": k, "value": v}
        for k, v in list(zip(schema_attr, credential_helper.credential_attrs))
    ]
    return cred_def_id, credential_attributes


@router.post("/credential")
async def issue_credential(
    credential_helper: CredentialHelper,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    cred_def_id, credential_attributes = await _credential_details(
        credential_helper, aries_controller
    )
    record = await issue_credentials(
        aries_controller,
        credential_helper.connection_id,
        credential_helper.schema_id,
        cred_def_id,
        credential_attributes,
    )
    return IssueCredentialResponse(credential=record)


@router.get("/records")
async def get_records(
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    return await aries_controller.issuer.get_records()


@router.get("/credential")
async def get_x_record(
    credential_x_id: str,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    return await aries_controller.issuer.get_record_by_id(credential_x_id)


@router.delete("/credential")
async def remove_credential(
    credential_id: str,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    return await aries_controller.credentials.remove_credential(credential_id)


@router.post("/problem-report")
async def problem_report(
    explanation: dict,
    credential_x_id: str,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    return await aries_controller.issuer.send_problem_report(
        credential_x_id, explanation=explanation["explanation"]
    )


@router.post("/credential/offer")
async def send_offer(
    credential_helper: CredentialHelper,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    cred_def_id, credential_attributes = await _credential_details(
        credential_helper, aries_controller
    )
    return await aries_controller.issuer.send_offer(
        credential_helper.connection_id, cred_def_id, credential_attributes
    )


@router.post("/credential/request")
async def send_credential_request(
    credential_x_id: str,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    return await aries_controller.issuer.send_request_for_record(credential_x_id)


@router.get("/credential/store")
async def store_credential(
    credential_x_id: str,
    credential_id: str,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    return await aries_controller.issuer.store_credential(
        credential_x_id, credential_id
    )


@router.post("/credential/proposal")
async def send_credential_proposal(
    credential_helper: CredentialHelper,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    cred_def_id, credential_attributes = await _credential_details(
        credential_helper, aries_controller
    )
    return await aries_controller.issuer.send_proposal(
        connection_id=credential_helper.connection_id,
        schema_id=credential_helper.schema_id,
        cred_def_id=cred_def_id,
        attributes=credential_attributes,
    )
