import logging
from aries_cloudcontroller.model.credential_preview import CredentialPreview
from aries_cloudcontroller.model.credential_proposal import CredentialProposal
from aries_cloudcontroller.model.v10_presentation_proposal_request import (
    V10PresentationProposalRequest,
)

from numpy import record

from dependencies import agent_selector

from aries_cloudcontroller import (
    AcaPyClient,
    V10CredentialCreate,
    V10CredentialExchange,
    V10CredentialBoundOfferRequest,
    V10CredentialExchangeListResult,
    V10CredentialFreeOfferRequest,
    V10CredentialIssueRequest,
    V10CredentialProblemReportRequest,
    V10CredentialProposalRequestMand,
    V10CredentialProposalRequestOpt,
    V10CredentialStoreRequest,
)

from pydantic import BaseModel
from typing import List, Optional
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
    """
    Helper methond that returns the credential definition id and credential attributes

    Parameters:
    -----------
    credential_helper: CredentialHelper
        payload for sending a credential helper

    Returns:
    ---------
    cred_def_id: credential definition id
    credential attributes: credential attributes
    """
    schema_attr = await get_schema_attributes(
        aries_controller, credential_helper.schema_id
    )
    cred_def_id = await write_credential_def(
        aries_controller, credential_helper.schema_id
    )
    credential_attributes = [
        {"name": k, "value": v}
        for k, v in list(zip(schema_attr, credential_helper.credential_attrs))
    ]
    return cred_def_id.credential_definition_id, credential_attributes


@router.post("/credential")
async def issue_credential(
    credential_helper: CredentialHelper,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Issue credential.

    Parameters:
    -----------
    credential_helper: CredentialHelper
        payload for sending a credential helper

    Returns:
    --------
    The response object from issuing a credential
    """
    cred_def_id, credential_attributes = await _credential_details(
        credential_helper, aries_controller
    )
    record = await issue_credentials(
        aries_controller,
        credential_helper.connection_id,
        credential_helper.schema_id,
        str(cred_def_id),
        credential_attributes,
    )
    async with record:
        content = await record.json()
    return content


@router.get("/records")
async def get_records(
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Get list of records.
    """
    result = await aries_controller.issue_credential_v1_0.get_records()
    async with result:
        content = await result.json()
    return content


@router.get("/credential")
async def get_x_record(
    credential_x_id: str,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Get record by id.

    Parameters:
    -----------
    credential_x_id: str
        credential exchange id

    """
    result = await aries_controller.issue_credential_v1_0.get_record(
        cred_ex_id=credential_x_id
    )
    async with result:
        content = await result.json()
    return content


@router.delete("/credential")
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
    The response object from removing a credential.

    """
    return await aries_controller.credentials.remove_credential(credential_id)


@router.post("/problem-report")
async def problem_report(
    explanation: dict,
    credential_x_id: str,
    aries_controller: AcaPyClient = Depends(agent_selector),
):

    """
    Create problem report for record.

    Parameters:
    -----------
    explanation: dict
    credential_x_id: str
        credential exchange id
    """
    return await aries_controller.issue_credential_v1_0.report_problem(
        cred_ex_id=credential_x_id,
        body=V10CredentialProblemReportRequest(description=explanation["description"]),
    )


@router.post("/credential/offer")
async def send_offer(
    cred_ex_id: str,
    counter_proposal: Optional[CredentialProposal] = CredentialProposal(),
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Send credential offer.

    Parameters:
    -----------

    Returns:
    --------
        The response object obtained from sending a credential offer.
    """
    return await aries_controller.issue_credential_v1_0.send_offer(
        cred_ex_id=cred_ex_id,
        body=V10CredentialBoundOfferRequest(
            counter_proposal=CredentialProposal(**counter_proposal.dict())
        ),
    )


@router.post("/credential/request", response_model=V10CredentialExchange)
async def send_credential_request(
    credential_x_id: str,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Send credential request.

    Parameters:
    -----------
    credential_helper: CredentialHelper
        payload for sending a credential request

    Returns:
    --------
        The response object obtained from sending a credential offer.
    """
    return await aries_controller.issue_credential_v1_0.send_request(
        cred_ex_id=credential_x_id
    )


@router.get("/credential/store")
async def store_credential(
    credential_x_id: str,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Store credential.

    Parameters:
    -----------
    credential_x_id: str
        credential exchange id
    credential_id: str
        credential identifier

    """
    return await aries_controller.issue_credential_v1_0.store_credential(
        cred_ex_id=credential_x_id, body={}
    )


@router.post("/credential/proposal")
async def send_credential_proposal(
    credential_helper: CredentialHelper,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Send credential proposal.

    Parameters:
    -----------
    credential_helper: CredentialHelper
        payload for sending a credential proposal

    Returns:
    ----------
        The response object from sending a credential proposal.
    """
    cred_def_id, credential_attributes = await _credential_details(
        credential_helper, aries_controller
    )
    result = await aries_controller.issue_credential_v1_0.send_proposal(
        body=V10CredentialProposalRequestOpt(
            connection_id=credential_helper.connection_id,
            schema_id=credential_helper.schema_id,
            cred_def_id=cred_def_id,
            credential_proposal=CredentialPreview(attributes=credential_attributes),
        )
    )
    async with result:
        content = await result.json()
    return content
