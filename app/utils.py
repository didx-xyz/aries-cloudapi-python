import logging
import os
from typing import Type, Union

from aries_cloudcontroller import AriesAgentController, AriesTenantController
from fastapi import Header, HTTPException

admin_url = os.getenv("ACAPY_ADMIN_URL")
admin_port = os.getenv("ACAPY_ADMIN_PORT")
is_multitenant = os.getenv("IS_MULTITENANT", False)

logger = logging.getLogger(__name__)


def validate_auth_header(auth_headers) -> Union[str, None]:
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
    if auth_headers["api_key"]:
        return "admin"
    elif auth_headers["wallet_id"] and auth_headers["tenant_jwt"]:
        return "tenant"
    else:
        raise HTTPException(
            status_code=400,
            detail="Bad headers. Either provide an api_key or both wallet_id and tenant_jwt",
        )


def controller_factory(
    auth_headers,
) -> Type[Union[AriesAgentController, AriesTenantController]]:
    """
    Aries Controller factory returning an
    AriesController object based on a request header

    Parameters:
    -----------
    auth_header: dict
        The dict representation of the request JSON Header auth attributes
        api_key or both wallet_id and tenant_jwt

    Returns:
    --------
    controller: AriesCloudController (object)
    """
    controller_type = validate_auth_header(auth_headers)
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
