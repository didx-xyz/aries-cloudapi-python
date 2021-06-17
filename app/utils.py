import os
from typing import Type, Union

from aries_cloudcontroller import AriesAgentController, AriesTenantController
from fastapi import Header, HTTPException

admin_url = os.getenv("ACAPY_ADMIN_URL")
admin_port = os.getenv("ACAPY_ADMIN_PORT")
is_multitenant = os.getenv("IS_MULTITENANT", False)


def validate_auth_header(req_header: Header) -> bool:
    """
    Validates the passed in request header to verify is has correct attributes
    api_key or (tenant_jwt and wallet_id)

    Parameters:
    -----------
    req_header: dict
        The dict representation of the request JSON Header

    Returns:
    --------
    is_valid_auth_header: bool
        True if either of the assumptions about request header are met
    """
    is_valid_tenant_header = "wallet_id" in req_header and "tenant_jwt" in req_header
    is_valid_admin_header = "api_key" in req_header
    is_valid_auth_header = req_header and (
        is_valid_tenant_header or is_valid_admin_header
    )
    return is_valid_auth_header


def controller_factory(
    req_header: Header,
) -> Type[Union[AriesAgentController, AriesTenantController]]:
    """
    Aries Controller factory returning an
    AriesController object based on a request header

    Parameters:
    -----------
    req_header: dict
        The dict representation of the request JSON Header

    Returns:
    --------
    controller: AriesCloudController (object)
    """
    if validate_auth_header(req_header):
        req_header = req_header if type(req_header) is dict else eval(req_header)
        if "api_key" in req_header:
            controller = AriesAgentController(
                admin_url=f"{admin_url}:{admin_port}",
                api_key=req_header["api_key"],
                is_multitenant=is_multitenant,
            )
        else:
            controller = AriesTenantController(
                admin_url=f"{admin_url}:{admin_port}",
                wallet_id=req_header["wallet_id"],
                tenant_jwt=req_header["tenant_jwt"],
            )
        return controller
    else:
        raise HTTPException(
            status_code=400,
            detail="Bad headers. Either provide an api_key or both wallet_id and tenant_jwt",
        )


def construct_zkp(zero_knowledge_proof: dict, schema_id: str):
    req_preds = []
    zkp = [
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
    return zkp
