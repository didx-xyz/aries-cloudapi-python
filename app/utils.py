from enum import Enum

import logging
import os
import re

# from deprecated import deprecated
from typing import Type, Union, List

from aries_cloudcontroller import AriesAgentController, AriesTenantController
from fastapi import HTTPException

# from agent_factory import ControllerType

EXTRACT_TOKEN_FROM_BEARER = r"Bearer (.*)"

yoma_agent_url = os.getenv("ACAPY_YOMA_AGENT_URL", "http://localhost:3021")
ecosystem_agent_url = os.getenv("ACAPY_ECOSYSTEM_AGENT_URL", "http://localhost:4021")
member_agent_url = os.getenv("ACAPY_MEMBER_AGENT_URL", "http://localhost:4021")

embedded_api_key = os.getenv("EMBEDDED_API_KEY", "adminApiKey")
logger = logging.getLogger(__name__)


def _extract_jwt_token_from_security_header(jwt_token):
    if not jwt_token:
        raise HTTPException(401)
    x = re.search(EXTRACT_TOKEN_FROM_BEARER, jwt_token)
    if x is not None:
        return x.group(1)
    else:
        raise HTTPException(401)


# @deprecated(
#     "logic moved to agent_factory - kept here because facade.create_controller still uses it"
# )
# def controller_factory(
#     controller_type: ControllerType,
#     x_api_key=None,
#     authorization_header=None,
#     x_wallet_id=None,
# ) -> Type[Union[AriesAgentController, AriesTenantController]]:
#     """
#     Aries Controller factory returning an
#     AriesController object based on a request header

#     Parameters:
#     -----------
#     auth_headers: dict
#         The header object containing wallet_id and jwt_token, or api_key

#     Returns:
#     --------
#     controller: AriesCloudController (object)
#     """
#     if not controller_type:
#         raise HTTPException(
#             status_code=400,
#             detail="Bad headers. Either provide an api_key or both wallet_id and tenant_jwt",
#         )
#     if controller_type == ControllerType.YOMA_AGENT:
#         if not x_api_key:
#             raise HTTPException(401)
#         return AriesAgentController(
#             admin_url=yoma_agent_url,
#             api_key=x_api_key,
#             is_multitenant=False,
#         )
#     elif controller_type == ControllerType.MEMBER_AGENT:
#         if not authorization_header:
#             raise HTTPException(401)
#         return AriesTenantController(
#             admin_url=member_agent_url,
#             api_key=embedded_api_key,
#             tenant_jwt=_extract_jwt_token_from_security_header(authorization_header),
#             wallet_id=x_wallet_id,
#         )
#     elif controller_type == ControllerType.ECOSYSTEM_AGENT:
#         if not authorization_header:
#             raise HTTPException(401)
#         return AriesTenantController(
#             admin_url=ecosystem_agent_url,
#             api_key=embedded_api_key,
#             tenant_jwt=_extract_jwt_token_from_security_header(authorization_header),
#             wallet_id=x_wallet_id,
#         )


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
