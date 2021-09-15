import logging

from dependencies import agent_selector
from facade import (
    get_schema_attributes,
    write_credential_def,
)
from aries_cloudcontroller import (
    AcaPyClient,
    V20CredExFree,
    V20CredOfferRequest,
    V20CredAttrSpec,
    V20CredFilter,
    V20CredFilterIndy,
    V20CredPreview,
    V20CredStoreRequest,
    V20IssueCredSchemaCore,
    V20CredIssueProblemReportRequest,
)
from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from typing import List, Optional, Tuple

# TypedDict from typing itself has some missing features for pydantic only available in 3.9
# https://pydantic-docs.helpmanual.io/usage/types/#typeddict
from typing_extensions import TypedDict

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generic/issuers/v2", tags=["issuer_v2"])


class ProblemReportExplanation(TypedDict):
    description: str


class CredentialBase(BaseModel):
    connection_id: str
    schema_id: str
    attributes: List[str]


class Credential(CredentialBase):
    connection_id: str
    schema_id: str
    cred_def_id: str
    attributes: List[str]


class CredentialOffer(Credential):
    comment: str = ""
    auto_issue: bool = True
    auto_remove: bool = True
    trace: bool = False


class Proposal(CredentialBase):
    pass


async def _credential_details(
    credential_helper: CredentialBase, aries_controller: AcaPyClient
) -> Tuple[str, V20CredPreview]:
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

    cred_preview = V20CredPreview(
        attributes=[
            V20CredAttrSpec(name=name, value=value)
            for name, value in list(zip(schema_attr, credential_helper.attributes))
        ]
    )
    return cred_def_id.credential_definition_id, cred_preview


@router.get("/records")
async def get_records(
    connection_id: Optional[str] = Header(None),
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Get list of records.

    Parameters:
    ------------
    connection_id: str (Optional)
    """
    return await aries_controller.issue_credential_v2_0.get_records(
        connection_id=connection_id
    )


@router.post("/credential")
async def send_credential(
    credential: Credential,
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
    cred_def_id, credential_preview = await _credential_details(
        credential, aries_controller
    )
    return await aries_controller.issue_credential_v2_0.issue_credential_automated(
        body=V20CredExFree(
            connection_id=credential.connection_id,
            credential_preview=V20CredPreview(attributes=credential_preview.attributes),
            auto_remove=False,
            filter=V20CredFilter(
                indy=V20CredFilterIndy(
                    cred_def_id=cred_def_id,
                )
            ),
        )
    )


@router.get("/credential")
async def get_credential(
    credential_id=Header(...),
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Get credential by credential id.

    Parameters:
    -----------
    credential_id: str
        credential identifier
    """
    # Same as in v1
    return await aries_controller.issue_credential_v2_0.get_record(
        cred_ex_id=credential_id
    )


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
    --------
    The response object from removing a credential.

    """
    # Same as in v1
    return await aries_controller.credentials.delete_record(credential_id=credential_id)


@router.post("/problem-report")
async def problem_report(
    explanation: ProblemReportExplanation,
    credential_x_id: str,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Create problem report for record.

    Parameters:
    -----------
    explanation: ProblemReportExplanation
    credential_x_id: str
        credential exchange id
    """
    return await aries_controller.issue_credential_v2_0.report_problem(
        cred_ex_id=credential_x_id,
        body=V20CredIssueProblemReportRequest(description=explanation["description"]),
    )


@router.post("/credential/offer")
async def send_offer(
    credential_offer: CredentialOffer,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Send credential offer.

    Parameters:
    -----------
    credential_offer: CredentialOffer
        payload for sending a credential offer

    Returns:
    --------
        The response object obtained from sending a credential offer.
    """
    cred_def_id, credential_preview = await _credential_details(
        credential_offer, aries_controller
    )
    return await aries_controller.issue_credential_v2_0.send_offer_free(
        body=V20CredOfferRequest(
            connection_id=credential_offer.connection_id,
            credential_preview=credential_preview,
            filter=V20CredFilter(
                indy=V20CredFilterIndy(
                    cred_def_id=cred_def_id,
                )
            ),
        )
    )


@router.post("/credential/request")
async def credential_request(
    credential_x_id=Header(...),
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Send credential request.

    Parameters:
    -----------
    credential_x_id: str
        credential exchange id

    Returns:
    --------
        The response object obtained from sending a credential request.
    """
    return await aries_controller.issue_credential_v2_0.send_request(
        cred_ex_id=credential_x_id, body={}
    )


@router.get("/credential/store")
async def store_credential(
    credential_x_id: str,
    credential_id: Optional[str] = None,
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
    return await aries_controller.issue_credential_v2_0.store_credential(
        cred_ex_id=credential_x_id,
        body=V20CredStoreRequest(credential_id=credential_id),
    )


@router.post("/credential/proposal")
async def send_credential_proposal(
    credential: Proposal,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Send credential proposal.

    Parameters:
    -----------
    credential: Proposal
        payload for sending a credential proposal

    Returns:
    ----------
        The response object from sending a credential proposal.
    """
    cred_def_id, credential_preview = await _credential_details(
        credential, aries_controller
    )

    return await aries_controller.issue_credential_v2_0.send_proposal(
        body=V20IssueCredSchemaCore(
            # connection_id is missing from 0.7.0 OpenAPI spec
            # https://github.com/hyperledger/aries-cloudagent-python/pull/1377
            connection_id=credential.connection_id,
            credential_preview=credential_preview,
            filter=V20CredFilter(
                indy=V20CredFilterIndy(
                    schema_id=credential.schema_id,
                    cred_def_id=cred_def_id,
                )
            ),
        )
    )
