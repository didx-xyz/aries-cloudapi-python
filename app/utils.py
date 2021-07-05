import logging
import os

import acapy_ledger_facade
import acapy_wallet_facade as wallet_facade
from schemas import DidCreationResponse
import ledger_facade
from fastapi import HTTPException
import re
from typing import List

EXTRACT_TOKEN_FROM_BEARER = r"Bearer (.*)"

yoma_agent_url = os.getenv("ACAPY_YOMA_AGENT_URL", "http://localhost:3021")
ecosystem_agent_url = os.getenv("ACAPY_ECOSYSTEM_AGENT_URL", "http://localhost:4021")
member_agent_url = os.getenv("ACAPY_MEMBER_AGENT_URL", "http://localhost:4021")

embedded_api_key = os.getenv("EMBEDDED_API_KEY", "adminApiKey")


logger = logging.getLogger(__name__)


def _extract_jwt_token_from_security_header(jwt_token):
    if not jwt_token:
        raise Exception(401)
    x = re.search(EXTRACT_TOKEN_FROM_BEARER, jwt_token)
    if x is not None:
        return x.group(1)
    else:
        raise Exception(401)


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
