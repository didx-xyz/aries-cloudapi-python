import logging
import os
from typing import Type, Union

from aries_cloudcontroller import AriesAgentController, AriesTenantController
from fastapi import Header, HTTPException

admin_url = os.getenv("ACAPY_ADMIN_URL")
admin_port = os.getenv("ACAPY_ADMIN_PORT")
is_multitenant = os.getenv("IS_MULTITENANT", False)

logger = logging.getLogger(__name__)


def get_controller_type(auth_headers) -> Union[str, None]:
    """
    Validates the passed in request header to verify is has correct attributes
    api_key or (tenant_jwt and wallet_id)

    Parameters:
    -----------
    auth_headers: dict
        The header object containing wallet_id and jwt_token, or api_key

    Returns:
    --------
    "admin", "tenant", or None: Union[str, None]
        (One of) the appropriate type(s) for the controller based on the headers provided
    """
    if "api_key" in auth_headers:
        return "admin"
    elif "wallet_id" in auth_headers and "tenant_jwt" in auth_headers:
        return "tenant"
    return None


def controller_factory(
    auth_headers,
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
    controller_type = get_controller_type(auth_headers)
    if not controller_type:
        raise HTTPException(
            status_code=400,
            detail="Bad headers. Either provide an api_key or both wallet_id and tenant_jwt",
        )
    if controller_type == "admin":
        return AriesAgentController(
            admin_url=f"{admin_url}:{admin_port}",
            api_key=auth_headers["api_key"],
            is_multitenant=is_multitenant,
        )
    else:
        return AriesTenantController(
            admin_url=f"{admin_url}:{admin_port}",
            wallet_id=auth_headers["wallet_id"],
            tenant_jwt=auth_headers["tenant_jwt"],
        )
