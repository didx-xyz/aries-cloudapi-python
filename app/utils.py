from enum import Enum

import logging
import os
from typing import Type, Union, List

from aries_cloudcontroller import AriesAgentController, AriesTenantController
from fastapi import Header, HTTPException

admin_url = os.getenv("ACAPY_ADMIN_URL")
yoma_agent_url = os.getenv("ACAPY_YOMA_AGENT_URL")
admin_port = os.getenv("ACAPY_ADMIN_PORT")
is_multitenant = os.getenv("IS_MULTITENANT", False)

logger = logging.getLogger(__name__)


class ControllerType(Enum):
    YOMA_AGENT = "yoma_agent"
    MEMBER_AGENT = "member_agent"


def controller_factory(
    controller_type: ControllerType, x_api_key=None, jwt_token=None
) -> Type[Union[AriesAgentController, AriesTenantController]]:
    """
    Aries Controller factory returning an
    AriesController object based on a request header

    Parameters:
    -----------
    auth_headers: dict
        The header object containing wallet_id and jwt_token, or api_key

    Returns:
    --------
    controller: AriesCloudController (object)
    """
    if not controller_type:
        raise HTTPException(
            status_code=400,
            detail="Bad headers. Either provide an api_key or both wallet_id and tenant_jwt",
        )
    if controller_type == ControllerType.YOMA_AGENT:
        return AriesAgentController(
            admin_url=yoma_agent_url,
            api_key=x_api_key,
            is_multitenant=False,
        )
    elif controller_type == ControllerType.MEMBER_AGENT:
        return AriesTenantController(
            admin_url=f"{admin_url}:{admin_port}",
            wallet_id=auth_headers["wallet_id"],
            tenant_jwt=auth_headers["tenant_jwt"],
        )


def construct_zkp(zero_knowledge_proof: List[dict], schema_id: str) -> list:
    if zero_knowledge_proof == [{}]:
        return []
    req_preds = []
    [
        req_preds.append(
            {
                "name": item["name"],
                "p_type": item["p_type"],
                "p_value": item["p_value"],
                "restrictions": [{"schema_id": schema_id}],
            }
        )
        for item in zero_knowledge_proof
    ]
    return req_preds


def construct_indy_proof_request(
    name_proof_request: str, schema_id: str, attr_req, req_preds
):
    indy_proof_request = {
        "name": name_proof_request,
        "version": schema_id.split(":")[-1],
        "requested_attributes": {
            f"0_{req_attr['name']}_uuid": req_attr for req_attr in attr_req
        },
        "requested_predicates": {
            f"0_{req_pred['name']}_GE_uuid": req_pred for req_pred in req_preds
        },
    }
    return indy_proof_request
