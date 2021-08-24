import logging

from dependencies import agent_selector

from aries_cloudcontroller import AcaPyClient
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
        cred_def_id,
        credential_attributes,
    )
    return IssueCredentialResponse(credential=record)


@router.get("/records")
async def get_records(
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Get list of records.
    """
    return await aries_controller.issuer.get_records()


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
    return await aries_controller.issuer.get_record_by_id(credential_x_id)


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
    return await aries_controller.issuer.send_problem_report(
        credential_x_id, explanation=explanation["description"]
    )


@router.post("/credential/offer")
async def send_offer(
    credential_helper: CredentialHelper,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Send credential offer.

    Parameters:
    -----------
    credential_helper: CredentialHelper
        payload for sending a credential offer

    Returns:
    --------
        The response object obtained from sending a credential offer.
    """
    cred_def_id, credential_attributes = await _credential_details(
        credential_helper, aries_controller
    )
    return await aries_controller.issuer.send_offer(
        credential_helper.connection_id, cred_def_id, credential_attributes
    )


@router.post("/credential/request")
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
    return await aries_controller.issuer.send_request_for_record(credential_x_id)


@router.get("/credential/store")
async def store_credential(
    credential_x_id: str,
    credential_id: str,
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
    return await aries_controller.issuer.store_credential(
        credential_x_id, credential_id
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
    return await aries_controller.issuer.send_proposal(
        connection_id=credential_helper.connection_id,
        schema_id=credential_helper.schema_id,
        cred_def_id=cred_def_id,
        attributes=credential_attributes,
    )
